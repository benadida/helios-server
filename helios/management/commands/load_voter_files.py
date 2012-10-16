"""
parse and set up voters from uploaded voter files

DEPRECATED

Ben Adida
ben@adida.net
2010-05-22
"""

from django.core.management.base import BaseCommand, CommandError
import datetime

from helios import utils as helios_utils

from helios.models import *

def process_csv_file(election, f):
    reader = csv_reader(f.read())
    
    num_voters = 0
    for voter in reader:
      # bad line
      if len(voter) < 1:
        continue
    
      num_voters += 1
      voter_id = voter[0]
      name = voter_id
      email = voter_id
    
      if len(voter) > 1:
        email = voter[1]
    
      if len(voter) > 2:
        name = voter[2]
    
      # create the user
      user = User.update_or_create(user_type='password', user_id=voter_id, info = {'password': helios_utils.random_string(10), 'email': email, 'name': name})
      user.save()
    
      # does voter for this user already exist
      voter = Voter.get_by_election_and_user(election, user)
    
      # create the voter
      if not voter:
        voter_uuid = str(uuid.uuid1())
        voter = Voter(uuid= voter_uuid, voter_type = 'password', voter_id = voter_id, name = name, election = election)
        voter.save()

    return num_voters


class Command(BaseCommand):
    args = ''
    help = 'load up voters from unprocessed voter files'
    
    def handle(self, *args, **options):
        # load up the voter files in order of last uploaded
        files_to_process = VoterFile.objects.filter(processing_started_at=None).order_by('uploaded_at')

        for file_to_process in files_to_process:
            # mark processing begins
            file_to_process.processing_started_at = datetime.datetime.utcnow()
            file_to_process.save()

            num_voters = process_csv_file(file_to_process.election, file_to_process.voter_file)

            # mark processing done
            file_to_process.processing_finished_at = datetime.datetime.utcnow()
            file_to_process.num_voters = num_voters
            file_to_process.save()
            
            
