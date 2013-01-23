# -*- coding: utf-8 -*-
import csv

from cStringIO import StringIO
from helios.models import *
from collections import defaultdict
from zeus.core import gamma_decode
from django.db.models import Count

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


SENSITIVE_DATA = ['admin_user', 'trustees', 'last_view_at']

def election_report(elections, votes_report=True, filter_sensitive=True):
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
            ('voting_ends_at', e.voting_ends_at),
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

        if filter_sensitive:
          for key in [k for k in entry if k in SENSITIVE_DATA]:
            del entry[key]

        yield entry


def election_votes_report(elections, include_alias=False, filter_sensitive=True):
    for vote in CastVote.objects.filter(election__in=elections,
                                    voter__excluded_at__isnull=True).values('voter__alias','voter',
                                                                           'cast_at').order_by('-cast_at'):
        entry = OrderedDict([
        ])
        if include_alias:
            entry['name'] = vote['voter__alias'],
        if not filter_sensitive:
            entry['name'] = Voter.objects.get(pk=vote['voter']).full_name
        if len(elections) > 1:
            entry['election'] = vote.election.name

        entry['date'] = vote['cast_at']
        yield entry


def election_voters_report(elections):
    for voter in Voter.objects.filter(election__in=elections,
                                      excluded_at__isnull=True).annotate(cast_count=Count('castvote')).order_by('voter_surname'):
        entry = OrderedDict([
            ('name', voter.voter_name),
            ('surname', voter.voter_surname),
            ('fathername', voter.voter_fathername),
            ('email', voter.voter_email),
            ('visited', bool(voter.last_visit)),
            ('votes_count', voter.cast_count)
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

def strforce(thing, encoding='utf8'):
    if isinstance(thing, unicode):
        return thing.encode(encoding)
    return str(thing)

def csv_from_party_results(election, party_results, outfile=None):
    if outfile is None:
        outfile = StringIO()
    csvout = csv.writer(outfile, dialect='excel', delimiter=',')
    writerow = csvout.writerow
    invalid_count = party_results['invalid_count']
    blank_count = party_results['blank_count']
    ballot_count = party_results['ballot_count']

    # election details
    DATE_FMT = "%d/%m/%Y %H:%S"
    voting_start = 'Έναρξη: %s' % (election.voting_starts_at.strftime(DATE_FMT))
    voting_end = 'Λήξη: %s' % (election.voting_ends_at.strftime(DATE_FMT))
    extended_until = ""
    if election.voting_extended_until:
      extended_until = 'Παράταση: %s' % \
              (election.voting_extended_until.strftime(DATE_FMT))

    writerow([strforce(election.name)])
    writerow([strforce(election.institution.name)])
    writerow([strforce(voting_start)])
    writerow([strforce(voting_end)])
    if extended_until:
        writerow([strforce(extended_until)])
    writerow([])


    writerow(['ΑΠΟΤΕΛΕΣΜΑΤΑ ΓΕΝΙΚΑ'])
    writerow(['ΣΥΝΟΛΟ', strforce(ballot_count)])
    writerow(['ΕΓΚΥΡΑ', strforce(ballot_count - invalid_count)])
    writerow(['ΑΚΥΡΑ', strforce(invalid_count)])
    writerow(['ΛΕΥΚΑ', strforce(blank_count)])

    writerow([])
    writerow(['ΑΠΟΤΕΛΕΣΜΑΤΑ ΣΥΝΔΥΑΣΜΩΝ'])
    party_counters = party_results['party_counts']
    for count, party in party_results['party_counts']:
        if party is None:
            continue
        writerow([strforce(party), strforce(count)])

    writerow([])
    writerow(['ΑΠΟΤΕΛΕΣΜΑΤΑ ΥΠΟΨΗΦΙΩΝ'])
    for count, candidate in sorted(party_results['candidate_counts']):
        writerow([strforce(candidate), strforce(count)])

    writerow([])
    writerow(['ΨΗΦΟΔΕΛΤΙΑ ΑΝΑΛΥΤΙΚΑ'])
    writerow(['Α/Α', 'ΣΥΝΔΥΑΣΜΟΣ', 'ΥΠΟΨΗΦΙΟΣ', 'ΕΓΚΥΡΟ/ΑΚΥΡΟ/ΛΕΥΚΟ'])
    counter = 0
    valid = 'ΕΓΚΥΡΟ'
    invalid = 'ΑΚΥΡΟ'
    blank = 'ΛΕΥΚΟ'
    empty = '---'
    for ballot in party_results['ballots']:
        counter += 1
        if not ballot['valid']:
            writerow([counter, empty, empty, invalid])
            continue
        party = ballot['party']
        if party is None:
            writerow([counter, empty, empty, blank])
            continue
        else:
            party = strforce(party)

        candidates = ballot['candidates']
        if not candidates:
            writerow([counter, party, empty, valid])
            continue

        for candidate in candidates:
            writerow([counter, party, strforce(candidate), valid])

    try:
        outfile.seek(0)
        return outfile.read()
    except:
        return None

