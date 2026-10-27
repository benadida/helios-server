"""
Merge users whose user_id differs only in case, for auth systems that match
user_ids case-insensitively (e.g. GitHub). See issue #506.

For each group of duplicates, one user is kept (the one that has logged in,
otherwise the oldest). Voters and election admin links are moved to it and
the other rows are deleted. Voter.voter_login_id is left untouched, since
published voter hashes are computed from it.

A group is skipped, and reported, if two of its users are voters in the same
election: that needs a person to decide which voter to keep.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
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


@transaction.atomic
def merge_group(survivor, duplicates):
  for dup in duplicates:
    Voter.objects.filter(user=dup).update(user=survivor)
    Election.objects.filter(admin=dup).update(admin=survivor)
    for election in Election.objects.filter(admins=dup):
      election.admins.remove(dup)
      election.admins.add(survivor)
    if dup.admin_p and not survivor.admin_p:
      survivor.admin_p = True
      survivor.save()
    dup.delete()


class Command(BaseCommand):
  help = 'Merge users whose user_id differs only in case (case-insensitive auth systems only)'

  def add_arguments(self, parser):
    parser.add_argument('--dry-run', action='store_true', help='report what would be merged without changing anything')

  def handle(self, *args, **options):
    dry_run = options['dry_run']
    merged = skipped = 0

    for users in find_duplicate_groups():
      survivor = pick_survivor(users)
      duplicates = [u for u in users if u.id != survivor.id]
      desc = "%s: keep %r (id %d), merge %s" % (
        survivor.user_type, survivor.user_id, survivor.id,
        ", ".join("%r (id %d)" % (u.user_id, u.id) for u in duplicates))

      conflicts = conflicting_elections(users)
      if conflicts:
        skipped += 1
        self.stdout.write("SKIPPED %s -- voter more than once in election(s): %s" % (desc, ", ".join(conflicts)))
        continue

      merged += 1
      self.stdout.write(("WOULD MERGE " if dry_run else "MERGED ") + desc)
      if not dry_run:
        merge_group(survivor, duplicates)

    self.stdout.write("%d group(s) %s, %d skipped" % (merged, "to merge" if dry_run else "merged", skipped))
