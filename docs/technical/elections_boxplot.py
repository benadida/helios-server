import json
import sys

import numpy as np
import matplotlib.pyplot as plt

with open(sys.argv[1], 'r') as elections_file:
    elections_json = json.load(elections_file)

voters_count = []
voters_cast_count = []
    
for election in elections_json.items():
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

ax.boxplot([voters_count, voters_cast_count], sym='gD')

ax.set_xticklabels(['Registered', 'Turnout'])

ax.yaxis.grid(True, linestyle='-', which='major', color='lightgrey',
              alpha=0.5)

plt.savefig('elections_to_date_boxplot.pdf', format='pdf')
plt.show()

