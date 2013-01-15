import sys
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from heliosauth.models import *
from zeus.models import Institution

import getpass

class Command(BaseCommand):
    args = '<username>'
    help = 'Create a non ecounting elections admin user'

    option_list = BaseCommand.option_list + (
    make_option('--name',
                       action='store',
                       dest='name',
                       default=None,
                       help='Full user name'),
    make_option('--superuser',
                       action='store_true',
                       dest='superuser',
                       default=False,
                       help='Give superuser permissions to user'),
    make_option('--institution',
                       action='store',
                       dest='institution',
                       default=None,
                       help='Institution id (used in --create-user)'),
    make_option('--create-institution',
                       action='store_true',
                       dest='create_institution',
                       default=False,
                       help='Institution id'),
    make_option('--create-user',
                       action='store_true',
                       dest='create_user',
                       default=False,
                       help='Create a new user'),
    make_option('--remove-user',
                       action='store_true',
                       dest='remove_user',
                       default=False,
                       help='Remove an existing user'),
    )

    def handle(self, *args, **options):
        reload(sys)
        sys.setdefaultencoding('utf-8')

        if options.get('create_institution'):
            if not len(args):
                print "Provide the institution name"
                exit()

            name = args[0].strip()
            Institution.objects.create(name=args[0].strip())

        if options.get('remove_user'):
            if not len(args):
                print "Provide a user id"
                exit()

            user = User.objects.get(pk=int(args[0].strip()))
            print "User has %d elections objects which will be removed" % user.elections.count()
            confirm = raw_input('Write "yes of course" if you are sure you want to remove \'%s\' ? ' % user.user_id)
            if confirm == "yes of course":
                user.delete()
            else:
                exit()
            print "User removed"

        if options.get('create_user'):
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

            inst_pk = options.get('institution')
            if not inst_pk:
                print "Please provide an institution id using --institution"
                exit()
            inst = Institution.objects.get(pk=int(inst_pk))

            password = getpass.getpass("Password:")
            password_confirm = getpass.getpass("Confirm password:")

            if password != password_confirm:
                print "Passwords don't match"
                exit()

            newuser = User()
            newuser.user_type = "password"
            newuser.admin_p = True
            newuser.info = {'name': name or username, 'password': password}
            newuser.name = name
            newuser.user_id = username
            newuser.superadmin_p = superadmin
            newuser.institution = inst
            newuser.ecounting_account = False
            newuser.save()

