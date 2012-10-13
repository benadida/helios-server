"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase
from zeus.helios_election import *
from helios.models import *
from zeus.models import *

class TestHeliosElection(TestCase):

    def test_election_workflow(self):

        e = Election(name="election test", uuid="test")
        e.save()


