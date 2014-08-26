import datetime
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth.hashers import make_password
from heliosauth.models import User
from zeus.models import Institution

from utils import SetUpAdminAndClientMixin

class TestHelpdeskWithClient(SetUpAdminAndClientMixin, TestCase):
    
    def setUp(self):
        super(TestHelpdeskWithClient, self).setUp()

        # create a manager user
        User.objects.create(
            user_type="password",
            user_id="test_manager",
            info={"password": make_password("test_manager")},
            admin_p=True,
            management_p=True,
            institution = self.institution,
            )
        self.manager_creds = {
            'username': 'test_manager',
            'password': 'test_manager'
            }

    def test_access_not_allowed_without_login(self):
        r = self.c.get(self.locations['helpdesk'], follow=True)
        self.assertEqual(r.status_code, 403)

    def test_simple_admin_not_allowed(self):
        self.c.post(self.locations['login'], self.login_data)
        r = self.c.get(self.locations['helpdesk'], follow=True)
        self.assertEqual(r.status_code, 403)

    def test_access_allowed_to_logged_manager(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(self.locations['helpdesk'], follow=True)
        self.assertEqual(r.status_code, 200)

    def test_create_institution_with_post(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        # before posting we must have only 1 institution
        self.assertEqual(Institution.objects.all().count(), 1)
        self.c.post(
            '/account_administration/institution_creation/',
           data={'name': 'new_test_inst'},
           follow=True
            )
        self.assertEqual(Institution.objects.all().count(), 2)
    
    def test_create_user_with_post(self):
        # there are already 2 users
        self.assertEqual(User.objects.all().count(), 2)
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        post_data = {
            'user_id': 'new_test_user',
            'institution': 'test_inst'
            }
        self.c.post(
            '/account_administration/user_creation/',
            post_data
            )
        self.assertEqual(User.objects.all().count(), 3)

    def test_delete_institution(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        # institution should not be deleted but
        # should be marked as disabled
        # create new institution with 0 users/elections
        inst = Institution.objects.create(name='inst_to_del')
        inst_id = inst.id
        self.c.get(
            '/account_administration/inst_deletion_confirmed/?id=%s'\
                % inst_id
            )
        inst = Institution.objects.get(name='inst_to_del')
        self.assertTrue(inst.is_disabled)

    def test_inst_with_users_cannot_be_disabled(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        # test_inst has already 2 users, 1 admin and 1 manager
        inst = Institution.objects.get(name='test_inst')
        inst_id = inst.id
        self.c.get(
            '/account_administration/inst_deletion_confirmed/?id=%s'\
                % inst_id
            )
        inst = Institution.objects.get(name='test_inst')
        self.assertEqual(inst.is_disabled, False)

    def test_inst_with_election_cannot_be_disabled(self):
        pass

    def test_delete_user(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        # current admin user has no elections and can be deleted
        u = User.objects.get(user_id='test_admin')
        u_id = u.id
        self.c.get(
            '/account_administration/user_deletion_confirmed/?id=%s'\
                % u_id
            )
        u = User.objects.get(user_id='test_admin')
        self.assertTrue(u.is_disabled)

    def test_user_with_election_cannot_be_disabled(self):
        start_date = datetime.datetime.now() + timedelta(hours=48)
        end_date = datetime.datetime.now() + timedelta(hours=56)
        election_form = {
            'trial': True,
            'election_module': 'simple',
            'name': 'test_election',
            'description': 'testing_election',
            'trustees': '',
            'voting_starts_at_0': start_date.strftime('%Y-%m-%d'),
            'voting_starts_at_1': start_date.strftime('%H:%M'),
            'voting_ends_at_0': end_date.strftime('%Y-%m-%d'),
            'voting_ends_at_1': end_date.strftime('%H:%M'),
            'help_email': 'test@test.com',
            'help_phone': 6988888888,
            'communication_language': 'el',
            }
        self.c.post(self.locations['login'], self.login_data)
        self.c.post(self.locations['create'], election_form) 
        u = User.objects.get(user_id='test_admin')
        self.assertEqual(u.elections.count(), 1)

        self.c.get(self.locations['logout'])
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_admin')
        u_id = u.id
        self.c.get(
            '/account_administration/user_deletion_confirmed/?id=%s'\
                % u_id
            )
        u = User.objects.get(user_id='test_admin')
        self.assertEqual(u.is_disabled, False)

