import argparse
import json
import itertools


from stv.stv import count_stv, Ballot

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Check stv results")

    parser.add_argument('-b', '--ballots', dest='ecounting_dict',
                        help='input ecounting_dict as json')
    parser.add_argument('-r', '--results', dest='ecounting_results',
                        help='input ecounting results as json')
    args = parser.parse_args()

    with open(args.ecounting_dict) as data_file:
        el_data = json.load(data_file)

    with open(args.ecounting_results) as ecounting_results_file:
        ecounting_results = json.load(ecounting_results_file)

    eligibles = el_data['numOfEligibles']
    hasLimit = el_data['hasLimit']
    ballots = el_data['ballots']
    input_ballots = []

    for ballot in ballots:
        orderedCandidateList = []
        for rank in range(1, len(ballot['votes'])+1):
            for vote in ballot['votes']:
                if vote['rank'] == rank:
                    orderedCandidateList.append(str(vote['candidateTmpId']))
        input_ballots.append(Ballot(orderedCandidateList))

    constituencies = {}
    schools = el_data['schools']
    for item in schools:
        school_name = item['Name']
        for candidate in item['candidates']:
            constituencies[str(candidate['candidateTmpId'])] = school_name
    #third item of count_result containes 'votes'
    draws = [str(c) for c in el_data['draws']]
    rnd_gen = draws if draws else None
    count_results = count_stv(input_ballots, eligibles,
                              droop=False,
                              constituencies=constituencies,
                              quota_limit=2 if hasLimit else 0,
                              rnd_gen=rnd_gen)

    
    #-------------------------------------------------------
    
    #take correct local_results format str8 from stv.py
    local_results = [] 
    for item in count_results[0]:
        for candidate in count_results[2]:
            if item[0] == candidate[0]:
                listed_item = list(item)
                temp_list = []
                temp_list.append(listed_item[0])
                temp_list.append(listed_item[1])
                temp_list.append(candidate[1])
                local_results.append(temp_list)



    for item in ecounting_results:
        item[0] = str(item[0])
    
    if ecounting_results != local_results:
        if len(ecounting_results) != len(local_results):
            print "Different number of elected candidates!"
        else:
            comp = ''.join([str(int(a == b)) for a, b in
                            zip(local_results, ecounting_results)])
            print "Round comparison: ", comp
            for c, a, b in zip(comp, local_results, ecounting_results):
                if c == '1':
                    continue
                if a[0] != b[0]:
                    print "Different Candidates Elected!"
                    print a
                    print b
                elif a[1] != b[1]:
                    print "Different Round of Election!"
                    print a
                    print b
                else:
                    for i, aa, bb in zip(itertools.count(), a[2], b[2]):
                        if aa == bb:
                            continue
                        print i, aa, bb
    else:
        pass  # print 'Results are exactly the same'

    same_candidates_elected = True
    same_rounds_of_election = True
    same_votes_on_round = True
    for item,item1 in itertools.izip(ecounting_results, local_results):
        if item[0] != item1[0]:
            same_candidates_elected = False
        if item[1] != item1[1]:
            same_rounds_of_election = False
        for rounds, rounds1 in itertools.izip(ecounting_results,local_results):
            if rounds[0] != rounds1[0] and rounds[1] != rounds1[1]:
                same_votes_on_round = False

    if not same_candidates_elected:
        print '- Candidates elected are different'
    else:
        pass  # print '* Same candidated were elected'

    if not same_rounds_of_election:
        print '- Rounds of election are different'
    else:
        pass  # print '* Candidate rounds of election are the same'

    if not same_votes_on_round:
        print '- Candidates took different number of votes each round'
    else:
        pass  # print '* Each round same number of votes were counted'
