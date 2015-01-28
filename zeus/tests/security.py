from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.test.client import Client

from zeus.models.zeus_models import Institution
from heliosauth.models import User
from helios.models import *

from utils import SetUpAdminAndClientMixin

# subclass order is significant
class TestUsersWithClient(SetUpAdminAndClientMixin, TestCase):

    def setUp(self):
        super(TestUsersWithClient, self).setUp()

    def test_user_on_login_page(self):
        r = self.c.get('/', follow=True)
        self.assertEqual(r.status_code, 200)

    def test_admin_login_with_creds(self):
        r = self.c.post(self.locations['login'], self.login_data, follow=True)
        self.assertEqual(r.status_code, 200)
        # user has no election so it redirects from /admin to /elections/new
        self.assertRedirects(r, self.locations['create'])

    def test_forbid_logged_admin_to_login(self):
        self.c.post(self.locations['login'], self.login_data)
        r = self.c.post(self.locations['login'], self.login_data)
        self.assertEqual(r.status_code, 403)

    def test_admin_login_wrong_creds(self):
        wrong_creds = {'username': 'wrong_admin', 'password': 'wrong_password'}
        r = self.c.post(self.locations['login'], wrong_creds)
        # if code is 200 user failed to login and wasn't redirected
        self.assertEqual(r.status_code, 200)

    def test_logged_admin_can_logout(self):
        self.c.post(self.locations['login'], self.login_data)
        r = self.c.get(self.locations['logout'], follow=True)
        self.assertRedirects(r, self.locations['home'])

class TestAdminsPermissions(SetUpAdminAndClientMixin, TestCase):
    
    def setUp(self):
        super(TestAdminsPermissions, self).setUp()
        #one admin exists, we need another one
        self.admin2 = User.objects.create(user_type="password",
                                         user_id="test_admin2",
                                         info={"password": make_password("test_admin2")},
                                         admin_p=True,
                                         institution=self.institution)
        self.login_data2 = {'username': 'test_admin2', 'password': 'test_admin2'}
        trustees_num = 2 
        trustees = "\n".join(",".join(['testName%x testSurname%x' %(x,x),
                                       'test%x@mail.com' %x]) for x in range(0,trustees_num))
        date1 = datetime.datetime.now() + timedelta(hours=48)
        date2 = datetime.datetime.now() + timedelta(hours=56)
        self.election_form = {
                              'trial': True,
                              'election_module': 'simple',
                              'name': 'test_election',
                              'description': 'testing_election',
                              'trustees': trustees,
                              'voting_starts_at_0': date1.strftime('%Y-%m-%d'),
                              'voting_starts_at_1': date1.strftime('%H:%M'),
                              'voting_ends_at_0': date2.strftime('%Y-%m-%d'),
                              'voting_ends_at_1': date2.strftime('%H:%M'),
                              'help_email': 'test@test.com',
                              'help_phone': 6988888888,
                              'communication_language': 'el',
                            }

    def login_and_create_election(self, login_data):
        self.c.post(self.locations['login'], login_data)
        r = self.c.post(self.locations['create'], self.election_form, follow=False)
        self.assertEqual(r.status_code, 302)
        self.c.get(self.locations['logout'])

    def create_elections_with_different_admins(self):
        self.login_and_create_election(self.login_data)
        self.login_and_create_election(self.login_data2)
        e = Election.objects.all()
        self.assertEqual(len(e), 2)
        #make dict with admin and his election(uuid)
        self.pairs = {}
        for election in e:
            self.pairs[election.admins.all()[0].user_id] = election.uuid

    def test_admins_cannot_access_other_elections(self):
        #login with admin2 and try to access election 1
        self.create_elections_with_different_admins()
        self.c.post(self.locations['login'], self.login_data2)
        r = self.c.get('/elections/%s/edit'% self.pairs['test_admin'])
        self.assertEqual(r.status_code, 403)
