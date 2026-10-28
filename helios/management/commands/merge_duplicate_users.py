"""
Merge users whose user_id differs only in case, for auth systems that match
user_ids case-insensitively (e.g. GitHub). See issue #506.

For each group of duplicates, one user is kept (the one that has logged in,
otherwise the oldest). Voters and election admin links are moved to it and
the other rows are deleted (including links on soft-deleted elections, which
would otherwise be cascade-deleted with the user).

Published voter hashes must not change. They are computed from
Voter.voter_login_id, or from the user's user_id when that is empty (voters
registered before #440). So existing voter_login_ids are left untouched, and
voters with an empty one get the old user_id written into it before being
moved to the kept user.

A group is skipped, and reported, if two of its users are voters in the same
election (a person must decide which voter to keep), if filling in a
voter_login_id would clash with another voter in that election, or if a voter
that would be moved has cast a ballot (voters who voted are never changed).

With --park, the groups skipped for the first or last of those reasons are
"parked" instead: each duplicate keeps its voters, its user_id is renamed to
'<user_id>.dup<id>' (not a valid GitHub username, so nobody can log in as it),
and its election admin links move to the kept user. Voter rows are not
changed, except that an empty voter_login_id is filled in with the old user_id
so the published hash stays the same. This includes voters who have voted
(only possible once voting has ended, see below): the hash, ballot and name
are unchanged, and each such fill is listed in the output. The person can then
log in again, and the case-insensitive index can be added. Still skipped, even
with --park:
- login-id clashes: filling in the voter_login_id is what keeps the hash
  stable, so those need a person to look;
- a duplicate that has voted in an election where voting is still open: once
  the kept user can log in, the person could vote a second time.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import Lower

from helios.models import Election, Voter
from helios_auth.auth_systems import AUTH_SYSTEMS, uses_case_insensitive_user_id
from helios_auth.models import User


def find_duplicate_groups():
  user_types = [t for t in AUTH_SYSTEMS if uses_case_insensitive_user_id(t)]
  keys = (User.objects.filter(user_type__in=user_types)
          .values('user_type', lower_user_id=Lower('user_id'))
          .annotate(n=Count('id')).filter(n__gt=1))
  for key in keys:
    yield list(User.objects.annotate(lower_user_id=Lower('user_id'))
               .filter(user_type=key['user_type'], lower_user_id=key['lower_user_id'])
               .order_by('id'))


def pick_survivor(users):
  # login sets token (upload leaves it None) and rewrites user_id to the provider's casing
  logged_in = [u for u in users if u.token is not None]
  return (logged_in or users)[0]


def conflicting_elections(users):
  return list(Voter.objects.filter(user__in=users).values('election__short_name')
              .annotate(n=Count('id')).filter(n__gt=1)
              .values_list('election__short_name', flat=True))


def voters_without_login_id(user):
  return Voter.objects.filter(user=user).filter(Q(voter_login_id__isnull=True) | Q(voter_login_id=''))


def elections_with_cast_votes(duplicates):
  return list(Voter.objects.filter(user__in=duplicates)
              .filter(Q(cast_at__isnull=False) | Q(castvote__isnull=False))
              .values_list('election__short_name', flat=True).distinct())


def login_id_clashes(duplicates):
  # elections where writing the duplicate's user_id into voter_login_id would hit unique (election, voter_login_id):
  # either another voter already has it, or the duplicate has several voters there that would all get it
  clashes = []
  for dup in duplicates:
    pending = voters_without_login_id(dup)
    for election_id in set(pending.values_list('election_id', flat=True)):
      if (pending.filter(election_id=election_id).count() > 1
          or Voter.objects.filter(election_id=election_id, voter_login_id=dup.user_id).exists()):
        clashes.append(Election.objects_with_deleted.get(id=election_id).short_name)
  return clashes


def voted_voters(duplicates):
  return Voter.objects.filter(user__in=duplicates).filter(Q(cast_at__isnull=False) | Q(castvote__isnull=False)).distinct()


def park_blockers(duplicates):
  # reasons not to park, even with --park
  still_open = sorted(set(v.election.short_name for v in voted_voters(duplicates) if not v.election.voting_has_stopped()))
  if still_open:
    return "voted in election(s) where voting is still open: %s" % ", ".join(still_open)
  return None


def elections_voted_more_than_once(users):
  # elections where this person has more than one voter that has voted: worth a look at that election's tally
  return list(Voter.objects.filter(user__in=users).filter(Q(cast_at__isnull=False) | Q(castvote__isnull=False))
              .values('election__short_name').annotate(n=Count('id', distinct=True)).filter(n__gt=1)
              .values_list('election__short_name', flat=True))


def voted_voters_to_fill(duplicates):
  # voters who have voted and will get voter_login_id filled in when parked (hash unchanged)
  return voted_voters(duplicates).filter(Q(voter_login_id__isnull=True) | Q(voter_login_id='')).select_related('user', 'election')


def move_admin_links(survivor, dup):
  Election.objects_with_deleted.filter(admin=dup).update(admin=survivor)
  for election in Election.objects_with_deleted.filter(admins=dup):
    election.admins.remove(dup)
    election.admins.add(survivor)
  if dup.admin_p and not survivor.admin_p:
    survivor.admin_p = True
    survivor.save()


def parked_user_id(dup):
  return "%s.dup%d" % (dup.user_id, dup.id)


@transaction.atomic
def merge_group(survivor, duplicates):
  for dup in duplicates:
    # keep these voters' published hash, which is currently computed from dup.user_id
    voters_without_login_id(dup).update(voter_login_id=dup.user_id)
    Voter.objects.filter(user=dup).update(user=survivor)
    move_admin_links(survivor, dup)
    dup.delete()


@transaction.atomic
def park_group(survivor, duplicates):
  for dup in duplicates:
    # keep these voters' published hash, which is currently computed from dup.user_id
    voters_without_login_id(dup).update(voter_login_id=dup.user_id)
    move_admin_links(survivor, dup)
    dup.user_id = parked_user_id(dup)
    dup.save()


class Command(BaseCommand):
  help = 'Merge users whose user_id differs only in case (case-insensitive auth systems only)'

  def add_arguments(self, parser):
    parser.add_argument('--dry-run', action='store_true', help='report what would be done without changing anything')
    parser.add_argument('--park', action='store_true',
                        help='park duplicates that would be skipped (voter twice in an election, or voted) instead of skipping them')

  def handle(self, *args, **options):
    dry_run = options['dry_run']
    park = options['park']
    merged = parked = skipped = 0

    for users in find_duplicate_groups():
      survivor = pick_survivor(users)
      duplicates = [u for u in users if u.id != survivor.id]
      desc = "%s: keep %r (id %d), merge %s" % (
        survivor.user_type, survivor.user_id, survivor.id,
        ", ".join("%r (id %d)" % (u.user_id, u.id) for u in duplicates))

      clashes = login_id_clashes(duplicates)
      if clashes:
        skipped += 1
        self.stdout.write("SKIPPED %s -- voter login id already taken in election(s): %s" % (desc, ", ".join(clashes)))
        continue

      reason = None
      conflicts = conflicting_elections(users)
      if conflicts:
        reason = "voter more than once in election(s): %s" % ", ".join(conflicts)
      else:
        voted = elections_with_cast_votes(duplicates)
        if voted:
          reason = "a voter to be moved has cast a ballot in election(s): %s" % ", ".join(voted)

      if reason and not park:
        skipped += 1
        self.stdout.write("SKIPPED %s -- %s" % (desc, reason))
        continue

      if reason:
        blocker = park_blockers(duplicates)
        if blocker:
          skipped += 1
          self.stdout.write("SKIPPED %s -- %s; cannot park: %s" % (desc, reason, blocker))
          continue

        parked += 1
        self.stdout.write("%s%s: keep %r (id %d), rename %s -- %s" % (
          "WOULD PARK " if dry_run else "PARKED ", survivor.user_type, survivor.user_id, survivor.id,
          ", ".join("%r (id %d) to %r" % (u.user_id, u.id, parked_user_id(u)) for u in duplicates), reason))
        for name in elections_voted_more_than_once(users):
          self.stdout.write("  WARNING: this person has more than one voter that has voted in election %s; check that election's tally" % name)
        for v in voted_voters_to_fill(duplicates):
          self.stdout.write("  %s voter_login_id = %r on voter %s, who has voted, in election %s (voting has ended; hash unchanged)" % (
            "will set" if dry_run else "set", v.user.user_id, v.uuid, v.election.short_name))
        if not dry_run:
          park_group(survivor, duplicates)
        continue

      merged += 1
      self.stdout.write(("WOULD MERGE " if dry_run else "MERGED ") + desc)
      if not dry_run:
        merge_group(survivor, duplicates)

    self.stdout.write("%d group(s) %s, %d skipped, %d %s" % (
      merged, "to merge" if dry_run else "merged", skipped, parked, "to park" if dry_run else "parked"))
