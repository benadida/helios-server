import json
import sys

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker

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
    
    "24ead444-6471-11e2-beac-aa000039f982",
    "a9d888ac-657c-11e2-a63b-aa000039f982",
    "706912c0-80c6-11e2-a6e6-aa000039f982",
    "531174f0-80c7-11e2-a6e6-aa000039f982",
    "a849dc6c-80d3-11e2-a3e2-aa000039f982",
    "29060eba-80da-11e2-94ff-aa000039f982",
    "1166c39a-80e8-11e2-9149-aa000039f982",
    "2ed0bd6c-8185-11e2-bde7-aa000039f982",
    "1d864052-84a7-11e2-b5f9-aa000039f982",
    "85c8c742-8d81-11e2-825d-aa000039f982",
    "74f9605c-909c-11e2-b119-aa000039f982",
    "71b459e0-9170-11e2-b119-aa000039f982",
    "e8936a84-9223-11e2-a129-aa000039f982",
    "b267444e-92e1-11e2-b496-aa000039f982",
    "de62313e-9436-11e2-bae5-aa000039f982",
    "6ca62002-97a9-11e2-8db9-aa000039f982",
    "baa050dc-9990-11e2-a4e0-aa000039f982",
    "0a1cd474-9b84-11e2-bf70-aa000039f982",
    "4c395f02-9c2f-11e2-aa42-aa000039f982",
    "55d422ea-9c34-11e2-8213-aa000039f982",
    "0027d0fc-9c3f-11e2-bf70-aa000039f982",
    "31f99dae-9ec4-11e2-8056-aa000039f982",
    "b1c9c3b8-a1fa-11e2-a441-aa000039f982",
    "1ca59f02-a108-11e2-a3f2-aa000039f982",
    "cff012ba-a59d-11e2-8658-aa000039f982",
    "4856d894-a808-11e2-8385-aa000039f982",
    "3b60e9e6-abea-11e2-8385-aa000039f982",
    "58f9e6e0-c13b-11e2-85f2-aa000039f982",
    "1832244a-c480-11e2-85f2-aa000039f982",
    "b3b28c8c-c8f1-11e2-8cc9-aa000039f982",
    "507d6492-c9c9-11e2-85f2-aa000039f982",
    "cf657c50-c9cd-11e2-858d-aa000039f982",
    "d30b7a68-cb9d-11e2-8385-aa000039f982",
    "e2085fd8-cba5-11e2-8385-aa000039f982",
    "c1f65fe2-cc36-11e2-86e2-aa000039f982",
    "cf14951c-ccf0-11e2-858d-aa000039f982",
    "29c50f16-cf47-11e2-8cc9-aa000039f982",
])

def order_elections_key(e):
    return e[1]['election']['voting_ended_at']

with open(sys.argv[1], 'r') as elections_file:
    elections_json = json.load(elections_file)

voters_count = []
voters_cast_count = []

elections_to_keep = dict((k, v) for k, v in elections_json.iteritems()
                         if k in to_keep) 

elections_to_discard = dict((k, v) for k, v in elections_json.iteritems()
                            if k not in to_keep) 

elections_lost = set(k for k in to_keep if k not in elections_json)

print "Lost:", elections_lost
print "To keep: ", len(elections_to_keep)
print "To discard: ", len(elections_to_discard)

for election in sorted(elections_to_keep.items(), key=order_elections_key):
    voters = election[1]['election']['voters_count']
    cast = election[1]['election']['voters_cast_count']
    voters_count.append(voters)
    voters_cast_count.append(cast)

print "Total voters", sum(voters_count)
print "Total voted", sum(voters_cast_count)
    
ind = np.arange(len(voters_count))
xvals = range(len(voters_count))
margin = 0
width = 0.35

fig = plt.figure()
ax = fig.add_subplot(111)

registered = ax.bar(margin+ind, voters_count, width, color='c', bottom = 0)
voted = ax.bar(margin+ind+width, voters_cast_count, width, color='m',
               bottom = 0)

ax.set_ylabel('Voters')
ax.set_title('Elections')
ax.set_xlim(-0.5, len(voters_count) + 0.5)
ax.set_xticks([])
ax.legend((registered[0], voted[0]), ('Registered', 'Turnout') )

# ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%d'))

# for i, bar in enumerate(registered):
#     height_registered = bar.get_height()
#     height_voted = voted[i].get_height()
#     participation = 100 * height_voted / height_registered
    # ax.text(bar.get_x()+bar.get_width()/2., 1.05*height_registered,
    #         '%d / %d = %.2f%%' % (int(height_registered), int(height_voted),
    #                           participation),
    #         ha='center', va='bottom')

plt.savefig('elections_to_date.pdf', format='pdf')
plt.show()

