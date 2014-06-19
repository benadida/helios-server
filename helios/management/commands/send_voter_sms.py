import sys
import os

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from heliosauth.models import *
from heliosauth.auth_systems.password import make_password
from helios.models import Voter, Poll, Election, csv_reader
from zeus import utils
from zeus import mobile as mobile_api

from zeus.models import Institution
from zeus import tasks

import getpass

class Command(BaseCommand):

    help = 'Notify voters by sms'

    option_list = BaseCommand.option_list + (
    make_option('--election',
                       action='store',
                       dest='election_uuid',
                       default=None,
                       help='Election UUID'),
    make_option('--poll',
                       action='store',
                       dest='poll_uuid',
                       default=None,
                       help='Poll UUID'),
    make_option('--template',
                       action='store',
                       dest='template',
                       default=None,
                       help='Path to the sms message template file'),
    make_option('--voters-mobiles-file',
                       action='store',
                       dest='mobiles_map_file',
                       default=None,
                       help='Path to the voters mobiles csv file'),
    make_option('--nodry',
                       action='store_false',
                       dest='dry',
                       default=True,
                       help='By default messages are printed to the ' + \
                            'screen. Set this flag to actually send ' + \
                            'messages using the sms API'),
    #make_option('--async',
                       #action='store_true',
                       #dest='async',
                       #default=False,
                       #help='Send messages asynchronously'),
    make_option('--list',
                       action='store_true',
                       dest='list_voters',
                       help='Just list the voters'),
    make_option('--voter',
                       action='store',
                       dest='voter_id',
                       default=None,
                       help='Voter registration number'),
    make_option('--resend',
                       action='store_true',
                       dest='resend',
                       default=False,
                       help='Resend messages even if last_sms_send_at ' + \
                            'flag is set to the voter instance'),
    make_option('--status',
                       action='store_true',
                       dest='status',
                       default=False,
                       help='Query status of the last sms sent.'),
    make_option('--voters-not-voted',
                       action='store_true',
                       dest='voters_not_voted',
                       default=False,
                       help='Exclude voters who have already voted.'),
    make_option('--voters-voted',
                       action='store_true',
                       dest='voters_voted',
                       default=False,
                       help='Exclude voters who haven\'t yet voted.'),
    make_option('--send-to',
                       action='store',
                       dest='send_to',
                       default=None,
                       help='Do not use voter mobile. Send message to the ' + \
                            'number provided instead (for testing).'),
    )

    def handle(self, *args, **options):
        reload(sys)
        sys.setdefaultencoding('utf-8')

        euuid = options.get('election_uuid')
        puuid = options.get('poll_uuid')
        voter_id = options.get('voter_id')
        dry = options.get('dry')
        list = options.get('list_voters')
        async = options.get('async')
        template = options.get('template')
        send_to = options.get('send_to')
        resend = options.get('resend')
        status = options.get('status')
        voters_voted = options.get('voters_voted')
        voters_not_voted = options.get('voters_not_voted')
        mobiles_map_file = options.get('mobiles_map_file')

        if voters_voted and voters_not_voted:
            raise CommandError("Please use only one of --voters-voted/--voters-not-voted")

        if not any([euuid, puuid]):
            raise CommandError("Please provide election or poll uuid.")

        if not template:
            raise CommandError("Please provide a template file.")

        if not os.path.exists(template):
            raise CommandError("Template file does not exist.")

        if dry and not status:
            print "Running in dry mode. No messages will be send."

        if mobiles_map_file and not os.path.exists(mobiles_map_file):
            raise CommandError("Voters mobiles file does not exist.")

        voters = Voter.objects.filter()
        all_voters = Voter.objects.filter()
        tplfd = file(template)
        tpl = tplfd.read()
        tplfd.close()

        election = None

        if euuid:
            voters = voters.filter(poll__election__uuid=euuid)
            election = Election.objects.get(uuid=euuid)
        if puuid:
            voters = voters.filter(poll__uuid=puuid)
            election = Poll.objects.select_related().get(uuid=puuid).election

        if voter_id:
            voters = voters.filter(voter_login_id=voter_id)


        if not status:
            print "Will send %d messages" % voters.count()

        mobiles_map = None
        if mobiles_map_file:
            mobiles_map = {}
            with open(mobiles_map_file, 'r') as f:
                data = f.read()
            reader = csv_reader(data, min_fields=3, max_fields=4)
            for fields in reader:
                voter_id = fields[0].strip()
                email = fields[1].strip()
                mobile = fields[2].strip()

                if voter_id in mobiles_map.keys():
                    raise CommandError(("Duplicate voter id found in mobiles"
                                        " csv file: %d") % int(voter_id))

                mobiles_map[voter_id] = {
                    'mobile': mobile,
                    'email': email
                }
                try:
                    utils.sanitize_mobile_number(mobile)
                except:
                    raise CommandError("Invalid mobile number: %s (%s)" % (
                        email, mobile
                    ))

            voters = voters.filter(voter_login_id__in=mobiles_map.keys())
            if voters.count() != len(mobiles_map.keys()):
                for voter_id in mobiles_map.keys():
                    if not all_voters.filter(voter_login_id=voter_id).count():
                        raise CommandError("Voter id not found in "
                                           "database: %s" % voter_id)
            for voter in voters:
                voter_id = voter.voter_login_id
                email = voter.voter_email
                csv_email = mobiles_map[voter_id]['email']
                if email != csv_email:
                    print repr(email), repr(csv_email)
                    raise CommandError("Voter email does not match the one"
                                       " in database: %s, %s, %s" % (
                                           voter_id,
                                           email,
                                           csv_email))

        if election:
            print "Using SMS API credentials for user '%s'" % \
                mobile_api.CREDENTIALS_DICT[election.uuid]['username']

        for voter in voters:
            if list:
                print voter.voter_email, voter.zeus_string
                continue

            task = tasks.send_voter_sms
            if status:
                task = tasks.check_sms_status

            if async:
                task = task.delay

            if status:
                if not voter.last_sms_code:
                    print "No SMS notification for %s" % (voter.zeus_string)
                    continue

                res = task(voter.last_sms_code)
                print "%s: %s" % (voter.zeus_string, res)
                continue

            self.stdout.write("Sending sms to %s " % (voter.zeus_string))

            if not resend and voter.last_sms_send_at:
                d = voter.last_sms_send_at.strftime("%d/%m/%Y %H:%M:%S")
                print "Skipping. Already send at %r" % d
                continue

            if dry:
                print

            if mobiles_map:
                mapped = mobiles_map.get(voter.voter_login_id)
                send_to = send_to or (mapped and mapped.get('mobile'))

            if not voter.voter_mobile and not send_to:
                print "Skipping. No voter mobile set"
                continue

            if send_to:
                print ("Overriding mobile number. Voter mobile: %s. "
                      "Will use : %s") % (voter.voter_mobile or "<not-set>",
                                             send_to)
            res, error = task(voter.pk, tpl, override_mobile=send_to,
                              resend=resend, dry=dry)
            if res:
                if not dry:
                    self.stdout.write(": ")
                print "[SUCCESS] Message sent successfully (%s)" % error
            else:
                if not dry:
                    self.stdout.write(": ")
                print "[ERROR] Message failed to send (%s)" % error
            if dry:
                print
