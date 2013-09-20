import sys
import os

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from heliosauth.models import *
from heliosauth.auth_systems.password import make_password
from helios.models import Voter

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
    make_option('--no-vote',
                       action='store_true',
                       dest='no_vote',
                       default=False,
                       help='Exclude voters who have already voted to the poll.'),
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

        if not any([euuid, puuid]):
            raise CommandError("Please provide election or poll uuid")

        if not template:
            raise CommandError("Please provide a template")

        if not os.path.exists(template):
            raise CommandError("Template file not found")

        if dry and not status:
            print "Running in dry mode. No messages will be send."


        voters = Voter.objects.filter()
        tplfd = file(template)
        tpl = tplfd.read()
        tplfd.close()

        if euuid:
            voters = voters.filter(poll__election__uuid=euuid)
        if puuid:
            voters = voters.filter(poll__uuid=puuid)

        if voter_id:
            voters = voters.filter(voter_login_id=voter_id)


        if not status:
            print "Will send %d messages" % voters.count()

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
                    print "o SMS notification for %s" % (voter.zeus_string)
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
