from helios.models import *
from collections import defaultdict
from zeus.core import gamma_decode

try:
  from collections import OrderedDict
except ImportError:
  from django.utils.datastructures import SortedDict as OrderedDict

def zeus_report(elections):
    return {
        'elections': elections,
        'votes': CastVote.objects.filter(election__in=elections, voter__excluded_at__isnull=True).count(),
        'voters': Voter.objects.filter(election__in=elections).count(),
        'voters_cast': CastVote.objects.filter(election__in=elections,
                                         voter__excluded_at__isnull=True).distinct('voter').count()
    }


def election_report(elections, votes_report=True):
    for e in elections:
        entry = OrderedDict([
            ('name', e.name),
            ('uuid', e.uuid),
            ('admin_user', e.admins.filter().values('user_id',
                                                        'ecounting_account')[0]),
            ('institution', e.institution.name),
            ('voting_started_at', e.voting_starts_at),
            ('voting_ended_at', e.voting_ended_at),
            ('voting_extended', bool(e.voting_extended_until)),
            ('voting_extended_until', e.voting_extended_until),
            ('has_department_limit', e.has_department_limit),
            ('eligibles_count', e.eligibles_count),
            ('departments', e.departments),
            ('trustees', list(e.trustee_set.filter(secret_key__isnull=True).values('name',
                                                                             'email'))),
            ('candidates', e.candidates),
        ])
        if votes_report:
            voters_added = e.voter_set.count()
            entry.update(OrderedDict([
                ('excluded_count', e.voter_set.filter(excluded_at__isnull=False).count()),
                ('audit_requests_count', e.auditedballot_set.filter(is_request=True).count()),
                ('audit_cast_count', e.auditedballot_set.filter(is_request=False).count()),
                ('voters_count', e.voter_set.count()),
                ('voters_cast_count', e.castvote_set.filter(voter__excluded_at__isnull=True).distinct('voter').count()),
                ('cast_count', e.castvote_set.count()),
                ('voters_visited_count', e.voter_set.filter(last_visit__isnull=False).count()),
                ('last_view_at',
                 e.voter_set.order_by('-last_visit')[0].last_visit if voters_added else None)
            ]))
        yield entry


def election_votes_report(elections, include_names=False):
    for vote in CastVote.objects.filter(election__in=elections,
                                    voter__excluded_at__isnull=True).order_by('-cast_at'):
        entry = OrderedDict([
            ('name', vote.voter.alias),
            ('date', vote.cast_at)
        ])
        if include_names:
            entry['name'] = vote.voter.full_name
        if len(elections) > 1:
            entry['election'] = vote.election.name
        yield entry


def election_voters_report(elections):
    for voter in Voter.objects.filter(election__in=elections,
                                      excluded_at__isnull=True).order_by('voter_surname'):
        entry = OrderedDict([
            ('name', voter.voter_name),
            ('surname', voter.voter_surname),
            ('fathername', voter.voter_fathername),
            ('email', voter.voter_email),
            ('visited', bool(voter.last_visit)),
            ('votes_count', voter.castvote_set.count())
        ])
        if len(elections) > 1:
            entry['election'] = vote.election.name
        yield entry


def _single_votes(results, clen):
    return filter(lambda sel: len(gamma_decode(sel, clen)) == 1, results)


def _get_choices_sums(results, choices_len):
    data = OrderedDict()
    for i in range(choices_len+1):
      data[str(i)] = 0

    for encoded in results:
        chosen_len = len(gamma_decode(encoded, choices_len))
        data[str(chosen_len)] = data[str(chosen_len)] + 1

    return data


def election_results_report(elections):
    for election in elections:
        if not election.result:
            entry = {}
        else:
            entry = OrderedDict([
                ('choices', len(election.questions[0]['answers'])),
                ('protest_votes_count', election.result[0].count(0)),
                ('total_count', len(election.result[0])),
                ('choices_sums', _get_choices_sums(election.result[0],
                                                   len(election.questions[0]['answers'])))
            ])
        if len(elections) > 1:
            entry['election'] = vote.election.name
        yield entry

