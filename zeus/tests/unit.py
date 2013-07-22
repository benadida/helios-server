from django.test import TestCase

from helios.models import *

class TestFeatures(TestCase):

    def test_election_features(self):
        e = Election.objects.create(name="New election")
        poll = e.polls.create(name="new")

        poll.questions_data =[{
            'answer_0': 'answer 1',
            'answers': ['answer 1'],
            'question': 'Question',
            'max_answers': '2',
            'min_answers': '1',
            'choice_type': 'choice'
        }]
        poll.update_answers()
        poll.save()

        voter = poll.voters.create(voter_email="v1@voters.com")

        e.zeus.create_zeus_key()
        e.zeus.compute_election_public()
        e.freeze()

        poll = Poll.objects.get(pk=poll.pk)
        import pdb; pdb.set_trace()
