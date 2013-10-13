"""
Testing Helios Features
"""

from helios.models import *
from helios_auth.models import *
import uuid

def generate_voters(election, num_voters = 1000, start_with = 1):
  # generate the user
  for v_num in range(start_with, start_with + num_voters):
    user = User(user_type='password', user_id='testuser%s' % v_num, name='Test User %s' % v_num)
    user.put()
    voter = Voter(uuid=str(uuid.uuid1()), election = election, voter_type=user.user_type, voter_id = user.user_id)
    voter.put()

def delete_voters(election):
  for v in Voter.get_by_election(election):
    v.delete()