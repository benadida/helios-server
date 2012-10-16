#!/usr/bin/env python

from zeus.core import gamma_decode, to_absolute_answers

def extract_publishables(zeus_finished):
    publishables = dict(zeus_finished)
    del publishables['zeus_secret']
    # duh
    return publishables

def extract_ecounting_ballots(zeus_results, nr_candidates):
    ballots = []
    append = ballots.append
    for i, encoded in enumerate(zeus_results):
        selection = gamma_decode(encoded, nr_candidates, nr_candidates)
        answers = to_absolute_answers(selection, nr_candidates)
        votes = [{ 'rank': j + 1, 'candidateTmpId': c }
                 for j, c in enumerate(answers)]
        ballot = { 'ballotSerialNumber': i + 1, 'votes': votes }
        append(ballot)

    return ballots


if __name__ == '__main__':
    import sys
    import json

    zeus_finished = json.load(sys.stdin)
    nr_candidates = len(zeus_finished['candidates'])
    zeus_results = zeus_finished['results']
    ballots = extract_ecounting_ballots(zeus_results, nr_candidates)
    json.dump(ballots, sys.stdout, indent=2)

