import json
import sys

import numpy as np
import scipy.stats as st

to_keep = set([
    "4edc7126-28ef-11e2-ab67-aa000039f982",
    "c6e6c970-2fdc-11e2-9459-aa000039f982",
    "0b35533e-250c-11e2-b13c-aa000039f982",
    "3eb123d6-226f-11e2-8cce-aa000039f982",
    "ac477410-2461-11e2-9d09-aa000039f982",
    "6ff62bbe-28df-11e2-a390-aa000039f982",
    "ae80de84-19b1-11e2-9f63-aa000039f982",
    "43024c9c-2802-11e2-9764-aa000039f982",
    "f48e5f34-1cf7-11e2-8c2b-aa000039f982",
    "9f68d874-1ccd-11e2-a708-aa000039f982",
    "7dd3a6d2-1f55-11e2-ae50-aa000039f982",
    "630108e2-1eb3-11e2-9543-aa000039f982",
    "1ad1b61a-2265-11e2-b2b6-aa000039f982",
    "5ba864d0-1ce4-11e2-9aaa-aa000039f982",
    "05577b00-20d3-11e2-ab53-aa000039f982",
    "5e4f6d64-235b-11e2-862d-aa000039f982",
    "842a5930-1e7f-11e2-a15b-aa000039f982",
    "4d818308-228b-11e2-bd9f-aa000039f982",
    "216dc370-2746-11e2-923e-aa000039f982",
    "ad95f546-3a26-11e2-bb7a-aa000039f982",
    "b31e35c0-3d67-11e2-8a51-aa000039f982",
    "174849f8-1939-11e2-8bf6-aa000039f982",
    "5b3b3350-48f5-11e2-9fbe-aa000039f982",
])


with open(sys.argv[1], 'r') as elections_file:
    elections_json = json.load(
        elections_file)

voters_count = []
voters_cast_count = []
    
for key, election in elections_json.iteritems():
    if key not in to_keep:
        continue
    voters = election['election']['voters_count']
    cast = election['election']['voters_cast_count']
    voters_count.append(voters)
    voters_cast_count.append(cast)

print "Total voters", sum(voters_count)
print "Total voted", sum(voters_cast_count)

voters_count_arr = np.array(voters_count)
voters_cast_count_arr = np.array(voters_cast_count)

voters_turnout_arr = 100 * voters_cast_count_arr / (1.0 * voters_count_arr)

print st.describe(voters_count_arr)
print st.describe(voters_cast_count_arr)
print st.describe(voters_turnout_arr)

