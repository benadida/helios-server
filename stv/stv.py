# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials provided
#     with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS''
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be interpreted
# as representing official policies, either expressed or implied, of
# GRNET S.A.

from operator import mul, itemgetter
from random import random, seed
import logging
import sys
import math
import csv
import argparse

SVT_LOGGER = 'SVT'
logger = logging.getLogger(SVT_LOGGER)

LOGGER_FORMAT = '%(message)s'
LOG_MESSAGE = "{action} {desc}"

class Action:
    COUNT_ROUND = "@ROUND"
    TRANSFER = ">TRANSFER"
    ELIMINATE = "-ELIMINATE"
    QUOTA ="!QUOTA"
    ELECT = "+ELECT"
    COUNT = ".COUNT"
    ZOMBIES = "~ZOMBIES"
    RANDOM = "*RANDOM"
    THRESHOLD = "^THRESHOLD"

class Ballot:
    """A ballot class for Single Transferable Voting.

    The ballot class contains an ordered list of candidates (in
    decreasing order of preference) and an ordered list of weights
    (new weights are added to the front of the list). The index of the
    current preference (for the first count and subsequent rounds)
    is also kept.

    """

    candidates = []
    weights = [1.0]
    current_preference = 0
    _value = 1.0

    def __init__(self, candidates=[]):
        self.candidates = candidates

    def add_weight(self, weight):
        self.weights.insert(0, weight)
        self._value *= weight

    def get_value(self):
        return self._value

def randomly_select_first(sequence, key, action, random_generator=None,
                          logger=logger):
    """Selects the first item of equals in a sorted sequence of items.

    For the given sorted sequence, returns the first item if it
    is different than the second; if there are ties so that there
    are items with equal values, it randomly selects among those items.
    The value of each item in the sequence is provided by applying the
    function key to the item. The action parameter indicates the context
    in which the random selection takes place (election or elimination).
    random_generator, if given, is the function that produces the random
    selection.

    """

    first_value = key(sequence[0])
    collected = []
    for item in sequence:
        if key(item) == first_value:
            collected.append(item)
        else:
            break
    index = 0
    selected = collected[index]
    num_eligibles = len(collected)
    if (num_eligibles > 1):
        if random_generator is None:
            index = int(random() * num_eligibles)
            selected = collected[index]
        else:
            if not random_generator:
                print "Missing value for random selection among ", collected
                sys.exit(1)
            selected = random_generator.pop(0)
        description = "{0} from {1} to {2}".format(selected, collected, action)
        logger.info(LOG_MESSAGE.format(action=Action.RANDOM, desc=description))
    return selected


def redistribute_ballots(selected, weight, hopefuls, allocated, vote_count,
                         logger=logger):
    """Redistributes the ballots from selected to the hopefuls.

    Redistributes the ballots currently allocated to the selected
    candidate. The ballots are redistributed with the given weight.
    The total ballot allocation is given by the allocated map, which
    is modified accordingly. The current vote count is given by
    vote_count and is adjusted according to the redistribution.

    """

    transferred = []
    # Keep a hash of ballot moves for logging purposes.
    # Keys are a tuple of the form (from_recipient, to_recipient, value)
    # where value is the current value of the ballot. Each tuple points
    # to the ballot being moved.
    moves = {}

    for ballot in allocated[selected]:
        reallocated = False
        i = ballot.current_preference + 1
        while not reallocated and i < len(ballot.candidates):
            recipient = ballot.candidates[i]
            if recipient in hopefuls:
                ballot.current_preference = i
                ballot.add_weight(weight)
                current_value = ballot.get_value()
                if recipient in allocated:
                    allocated[recipient].append(ballot)
                else:
                    allocated[recipient] = [ballot]
                if recipient in vote_count:
                    vote_count[recipient] += current_value
                else:
                    vote_count[recipient] = current_value
                vote_count[selected] -= current_value
                reallocated = True
                if (selected, recipient, current_value) in moves:
                    moves[(selected, recipient, current_value)].append(ballot)
                else:
                    moves[(selected, recipient, current_value)] = [ballot]
                transferred.append(ballot)
            else:
                i += 1
    for move, ballots in moves.iteritems():
        times = len(ballots)
        description =  "from {0} to {1} {2}*{3}={4}".format(move[0],
                                                            move[1],
                                                            times,
                                                            move[2],
                                                            times * move[2])
        logger.debug(LOG_MESSAGE.format(action=Action.TRANSFER,
                                        desc=description))

    allocated[selected][:] = [x for x in allocated[selected]
                              if x not in transferred ]

def elect_reject(candidate, vote_count, constituencies, quota_limit,
                 current_round, elected, rejected, constituencies_elected,
                 logger=logger):
    """Elects or rejects the candidate, based on quota restrictions.

    If there are no quota limits, the candidate is elected. If there
    are quota limits, the candidate is either elected or rejected, if
    the quota limits are exceeded. The elected and rejected lists
    are modified accordingly, as well as the constituencies_elected map.

    Returns true if the candidate is elected, false otherwise.
    """


    quota_exceeded = False
    # If there is a quota limit, check if it is exceeded
    if quota_limit > 0 and candidate in constituencies:
        current_constituency = constituencies[candidate]
        if constituencies_elected[current_constituency] >= quota_limit:
            quota_exceeded = True
    # If the quota limit has been exceeded, reject the candidate
    if quota_exceeded:
        rejected.append((candidate, current_round, vote_count[candidate]))
        d = candidate + " = " + str(vote_count[candidate])
        msg = LOG_MESSAGE.format(action=Action.QUOTA, desc=d)
        logger.info(msg)
        return False
    # Otherwise, elect the candidate
    else:
        elected.append((candidate, current_round, vote_count[candidate]))
        if constituencies:
            current_constituency = constituencies[candidate]
            constituencies_elected[current_constituency] += 1
        d = candidate + " = " + str(vote_count[candidate])
        msg = LOG_MESSAGE.format(action=Action.ELECT, desc=d)
        logger.info(msg)
        return True

def count_description(vote_count, candidates):
    """Returns a string with count results.

    The string is of the form of {0} = {1} separated by ; where each {0}
    is a candidate and each {1} is the corresponding vote count.
    """

    return  ';'.join(map(lambda x: "{0} = {1}".format(x, vote_count[x]),
                         candidates))


def count_stv(ballots, seats, droop = True, constituencies = None,
              quota_limit = 0, rnd_gen=None, logger=logger):
    """Performs a STV vote for the given ballots and number of seats.

    If droop is true the election threshold is calculated according to the
    Droop quota:
            threshold = int(1 + (len(ballots) / (seats + 1.0)))
    otherwise it is calculated according to the following formula:
            threshold = int(math.ceil(1 + len(ballots) / (seats + 1.0)))
    The constituencies argument is a map of candidates to constituencies, if
    any. The quota_limit, if different than zero, is the limit of candidates
    that can be elected by a constituency.
    """

    allocated = {} # The allocation of ballots to candidates
    vote_count = {} # A hash of ballot counts, indexed by candidates
    candidates = [] # All candidates
    elected = [] # The candidates that have been elected
    hopefuls = [] # The candidates that may be elected
    # The candidates that have been eliminated because of low counts
    eliminated = []
    # The candidates that have been eliminated because of quota restrictions
    rejected = []
    # The number of candidates elected per constituency
    constituencies_elected = {}

    for (candidate, constituency) in constituencies.iteritems():
        constituencies_elected[constituency] = 0
        if candidate not in allocated:
            allocated[candidate] = []
        if candidate not in candidates: # check not really needed
            candidates.append(candidate)
            vote_count[candidate] = 0

    seed()

    if droop:
        threshold = int(1 + (len(ballots) / (seats + 1.0)))
    else:
        threshold = int(math.ceil(1 + len(ballots) / (seats + 1.0)))

    logger.info(LOG_MESSAGE.format(action=Action.THRESHOLD,
                                   desc=threshold))
    # Do initial count
    for ballot in ballots:
        selected = ballot.candidates[0]
        for candidate in ballot.candidates:
            if candidate not in candidates:
                candidates.append(candidate)
                vote_count[candidate] = 0
            if candidate not in allocated:
                allocated[candidate] = []
        allocated[selected].append(ballot)
        vote_count[selected] += 1

    # In the beginning, all candidates are hopefuls
    hopefuls = [x for x in candidates]

    # Start rounds
    current_round = 1
    num_elected = len(elected)
    num_hopefuls = len(hopefuls)
    full_data = []
    for item in candidates:
        full_data.append([item, []])
    while num_elected < seats and num_hopefuls > 0:
        # Log round
        logger.info(LOG_MESSAGE.format(action=Action.COUNT_ROUND,
                                       desc=current_round))
        # Log count
        description  = count_description(vote_count, hopefuls)

        # using this for testing
        data = description.split(';')
        for item in data:
            item = item.split('=')
            item[0] = item[0].strip()
            item[1] = item[1].strip()
            for candidate in full_data:
                if candidate[0] == item[0]:
                    vote_no_decimal = float(item[1]) * 10000
                    vote_rounded = int(round(vote_no_decimal))
                    candidate[1].append([current_round, vote_rounded])

        logger.info(LOG_MESSAGE.format(action=Action.COUNT,
                                       desc=description))
        hopefuls_sorted = sorted(hopefuls, key=vote_count.get, reverse=True )
        # If there is a surplus record it so that we can try to
        # redistribute the best candidate's votes according to their
        # next preferences
        surplus = vote_count[hopefuls_sorted[0]] - threshold
        # If there is either a candidate with surplus votes, or
        # there are hopeful candidates beneath the threshold.
        if surplus >= 0 or num_hopefuls <= (seats - num_elected):
            best_candidate = randomly_select_first(hopefuls_sorted,
                                                   key=vote_count.get,
                                                   action=Action.ELECT,
                                                   random_generator=rnd_gen,
                                                   logger=logger)
            if best_candidate not in hopefuls:
                print "Not a valid candidate: ",best_candidate
                sys.exit(1)
            hopefuls.remove(best_candidate)
            was_elected = elect_reject(best_candidate, vote_count,
                                       constituencies, quota_limit,
                                       current_round,
                                       elected, rejected,
                                       constituencies_elected,
                                       logger=logger)
            if not was_elected:
                redistribute_ballots(best_candidate, 1.0, hopefuls, allocated,
                                     vote_count, logger=logger)
            if surplus > 0:
                # Calculate the weight for this round
                weight = float(surplus) / vote_count[best_candidate]
                # Find the next eligible preference for each one of the ballots
                # cast for the candidate, and transfer the vote to that
                # candidate with its value adjusted by the correct weight.
                redistribute_ballots(best_candidate, weight, hopefuls,
                                     allocated, vote_count, logger=logger)
        # If nobody can get elected, take the least hopeful candidate
        # (i.e., the hopeful candidate with the less votes) and
        # redistribute that candidate's votes.
        else:
            hopefuls_sorted.reverse()
            worst_candidate = randomly_select_first(hopefuls_sorted,
                                                    key=vote_count.get,
                                                    action=Action.ELIMINATE,
                                                    random_generator=rnd_gen,
                                                    logger=logger)
            hopefuls.remove(worst_candidate)
            eliminated.append(worst_candidate)
            d = worst_candidate + " = " + str(vote_count[worst_candidate])
            msg = LOG_MESSAGE.format(action=Action.ELIMINATE, desc=d)
            logger.info(msg)
            redistribute_ballots(worst_candidate, 1.0, hopefuls, allocated,
                                 vote_count, logger=logger)

        current_round += 1
        num_hopefuls = len(hopefuls)
        num_elected = len(elected)

    # If there is either a candidate with surplus votes, or
    # there are hopeful candidates beneath the threshold.
    while (seats - num_elected) > 0 and len(eliminated) > 0:
        logger.info(LOG_MESSAGE.format(action=Action.COUNT_ROUND,
                                       desc=current_round))
        description  = count_description(vote_count, eliminated)

        logger.info(LOG_MESSAGE.format(action=Action.ZOMBIES,
                                       desc=description))
        best_candidate = eliminated.pop()
        elect_reject(best_candidate, vote_count, constituencies,
                     quota_limit, current_round,
                     elected, rejected, constituencies_elected,
                     logger=logger)
        current_round += 1

    return elected, vote_count, full_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Perform STV')
    parser.add_argument('-b', '--ballots', default='sys.stdin',
                        dest='ballots_file', help='input ballots file')
    parser.add_argument('-n', '--not_droop', action="store_false",
                        dest='droop', help="don't use droop quota")
    parser.add_argument('-s', '--seats', type=int, default=0,
                        dest='seats', help='number of seats')
    parser.add_argument('-c', '--constituencies',
                        dest='constituencies_file',
                        help='input constituencies file')
    parser.add_argument('-q', '--quota', type=int, default=0,
                        dest='quota', help='constituency quota')
    parser.add_argument('-r', '--random', nargs='*',
                        dest='random', help='random selection results')
    parser.add_argument('-l', '--loglevel', default=logging.INFO,
                        dest='loglevel', help='logging level')
    args = parser.parse_args()

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    logger = logging.getLogger(SVT_LOGGER)
    logger.setLevel(args.loglevel)
    logger.addHandler(stream_handler)

    ballots = []
    ballots_file = sys.stdin
    if args.ballots_file != 'sys.stdin':
        ballots_file = open(args.ballots_file, 'U')
    ballots_reader = csv.reader(ballots_file, delimiter=',',
                                quotechar='"',
                                skipinitialspace=True)
    for ballot in ballots_reader:
        ballots.append(Ballot(ballot))

    if args.seats == 0:
        args.seats = len(ballots) / 2

    constituencies = {}
    if args.constituencies_file:
        constituencies_file = open(args.constituencies_file, 'U')
        constituencies_reader = csv.reader(constituencies_file,
                                           delimiter=',',
                                           quotechar='"',
                                           skipinitialspace=True)
        constituency_id = 0
        for constituency in constituencies_reader:
            for candidate in constituency:
                constituencies[candidate] = constituency_id
            constituency_id += 1

    (elected, vote_count, full_data) = count_stv(ballots, args.seats, args.droop,
                                      constituencies,
                                      args.quota,
                                      args.random,
                                      logger=logger)

    print "Results:"
    for result in elected:
        print result
