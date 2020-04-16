"""
Testing Helios Features
"""

import uuid

from helios.models import Voter
from helios_auth.models import User


def generate_voters(election, num_voters=1000, start_with=1):
    # generate the user
    for v_num in range(start_with, start_with + num_voters):
        user = User(user_type='password', user_id='testuser%s' % v_num, name='Test User %s' % v_num)
        user.save()
        voter = Voter(uuid=str(uuid.uuid1()), election=election, voter_type=user.user_type, voter_id=user.user_id)
        voter.save()


def delete_voters(election):
    for v in Voter.get_by_election(election):
        v.delete()
