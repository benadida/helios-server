import json
import sys

import numpy as np
import scipy.stats as st

to_keep = set([
    "ae80de84-19b1-11e2-9f63-aa000039f982", # Harokopeio University
    "174849f8-1939-11e2-8bf6-aa000039f982", # TEI Piraeus
    "f48e5f34-1cf7-11e2-8c2b-aa000039f982", # Ionian University
    "9f68d874-1ccd-11e2-a708-aa000039f982", # TEI Patras
    "7dd3a6d2-1f55-11e2-ae50-aa000039f982", # University of Thrace
    "630108e2-1eb3-11e2-9543-aa000039f982", # TEI Athens
    "1ad1b61a-2265-11e2-b2b6-aa000039f982", # University of Thessaly
    "5ba864d0-1ce4-11e2-9aaa-aa000039f982", # Panteion University
    "05577b00-20d3-11e2-ab53-aa000039f982", # University of Thessaloniki
    "5e4f6d64-235b-11e2-862d-aa000039f982", # AUEB
    "842a5930-1e7f-11e2-a15b-aa000039f982", # Agricultural University of Athens
    "4d818308-228b-11e2-bd9f-aa000039f982", # University of Ioannina
    "3eb123d6-226f-11e2-8cce-aa000039f982", # University of Crete
    "ac477410-2461-11e2-9d09-aa000039f982", # University of Macedonia
    "0b35533e-250c-11e2-b13c-aa000039f982", # University of Patras
    "216dc370-2746-11e2-923e-aa000039f982", # Athens School of Fine Arts
    "43024c9c-2802-11e2-9764-aa000039f982", # University of the Aegean
    "4edc7126-28ef-11e2-ab67-aa000039f982", # University of Athens
    "6ff62bbe-28df-11e2-a390-aa000039f982", # University of Piraeus
    "c6e6c970-2fdc-11e2-9459-aa000039f982", # University of the Peloponnese
    "ad95f546-3a26-11e2-bb7a-aa000039f982", # Technical University of Crete
    "b31e35c0-3d67-11e2-8a51-aa000039f982", # NTUA
    "5b3b3350-48f5-11e2-9fbe-aa000039f982", # TEI Piraeus
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

