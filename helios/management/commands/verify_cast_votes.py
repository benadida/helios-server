"""
verify cast votes that have not yet been verified

Ben Adida
ben@adida.net
2010-05-22
"""

from django.core.management.base import BaseCommand

from helios.models import CastVote


def get_cast_vote_to_verify():
    # fixme: add "select for update" functionality here
    votes = CastVote.objects.filter(verified_at=None, invalidated_at=None).order_by('-cast_at')
    if len(votes) > 0:
        return votes[0]
    else:
        return None

class Command(BaseCommand):
    args = ''
    help = 'verify votes that were cast'
    
    def handle(self, *args, **options):
        while True:
            cast_vote = get_cast_vote_to_verify()
            if not cast_vote:
                break

            cast_vote.verify_and_store()

        # once broken out of the while loop, quit and wait for next invocation
        # this happens when there are no votes left to verify
            
