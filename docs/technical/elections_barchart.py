import json
import sys

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker

def order_elections_key(e):
    e[1]['election']['voting_ended_at']

with open(sys.argv[1], 'r') as elections_file:
    elections_json = json.load(elections_file)

voters_count = []
voters_cast_count = []
    
for election in sorted(elections_json.items(), key=order_elections_key):
    voters = election[1]['election']['voters_count']
    cast = election[1]['election']['voters_cast_count']
    voters_count.append(voters)
    voters_cast_count.append(cast)

print "Total voters", sum(voters_count)
print "Total voted", sum(voters_cast_count)
    
num_stacks = len(voters_count)
print num_stacks
ind = np.arange(num_stacks)
margin = 1.5
width = 0.35

fig = plt.figure()
ax = fig.add_subplot(111)

registered = ax.bar(margin+ind, voters_count, width, color='c', bottom = 0)
voted = ax.bar(margin+ind+width, voters_cast_count, width, color='m',
               bottom = 0)

ax.set_ylabel('Voters')
ax.set_title('Elections')
ax.set_xticks([])
ax.legend((registered[0], voted[0]), ('Registered', 'Turnout') )

# ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%d'))

for i, bar in enumerate(registered):
    height_registered = bar.get_height()
    height_voted = voted[i].get_height()
    participation = 100 * height_voted / height_registered
    # ax.text(bar.get_x()+bar.get_width()/2., 1.05*height_registered,
    #         '%d / %d = %.2f%%' % (int(height_registered), int(height_voted),
    #                           participation),
    #         ha='center', va='bottom')

plt.savefig('elections_to_date.pdf', format='pdf')
plt.show()

