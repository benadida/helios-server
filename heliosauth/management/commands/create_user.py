from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from heliosauth.models import *

import getpass

class Command(BaseCommand):
    args = '<username>'
    help = 'Create a non ecounting elections admin user'

    option_list = BaseCommand.option_list + (make_option('--name',
                       action='store',
                       dest='name',
                       default=None,
                       help='Name of the user'),
    make_option('--superuser',
                       action='store_true',
                       dest='superuser',
                       default=False,
                       help='Give superuser permissions to user'),
    make_option('--institution',
                       action='store',
                       dest='institution',
                       default=1,
                       help='Institution id'),
    )

    def handle(self, *args, **options):
        if len(args) == 0:
            print "Please provide a username"
            exit()

        username = args[0].strip()
        superadmin = options.get('superuser', False)
        name = options.get('name', None)

        try:
            existing = User.objects.get(user_id=username)
        except User.DoesNotExist:
            existing = False

        if existing:
            print "User %s, already exists" % username
            exit()

        newuser = User()
        newuser.user_type = "password"
        newuser.admin_p = True
        newuser.info = {'name': name or username, 'password': getpass.getpass("Password:")}
        newuser.name = name
        newuser.user_id = username
        newuser.superadmin_p = superadmin
        newuser.institution_id = options.get('institution')
        newuser.ecounting_account = False
        newuser.save()

