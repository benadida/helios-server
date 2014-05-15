from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.test.client import Client
from zeus.models.zeus_models import Institution
from heliosauth.models import User


class TestUsersWithClient(TestCase):

    def setUp(self):
        institution = Institution.objects.create(name="test_inst")
        self.admin = User.objects.create(user_type="password", user_id="test_admin",
                                         info={"password": make_password("test_admin")},
                                         admin_p=True, institution=institution)
        self.login_location = '/auth/auth/login'
        self.login_data = {'username': 'test_admin', 'password': 'test_admin'}

    def get_client(self):
        return Client()

    def test_user_on_login_page(self):
        client = self.get_client()
        r = client.get('/', follow=True)
        self.assertEqual(r.status_code, 200)

    def test_admin_login_with_creds(self):
        client = self.get_client()
        r = client.post(self.login_location, self.login_data, follow=True)
        self.assertEqual(r.status_code, 200)
        #user has no election so it redirects from /admin to /elections/new
        self.assertRedirects(r, '/elections/new')

    def test_forbid_logged_admin_to_login(self):
        client = self.get_client()
        client.post(self.login_location, self.login_data)
        r = client.post(self.login_location, self.login_data)
        self.assertEqual(r.status_code, 403)

    def test_admin_login_wrong_creds(self):
        client = self.get_client()
        wrong_creds = {'username': 'wrong_admin', 'password': 'wrong_password'}
        r = client.post(self.login_location, wrong_creds)
        #if code is 200 user failed to login and wasn't redirected
        self.assertEqual(r.status_code, 200)

    def test_logged_admin_can_logout(self):
        client = self.get_client()
        client.post(self.login_location, self.login_data)
        logout_location = '/auth/auth/logout'
        r = client.get(logout_location, follow=True)
        self.assertRedirects(r, '/')

''' 
class CheckElection(TestCase):
    def setUp(self):
        institution = Institution.objects.create(name="test_inst")
        admin = User.objects.create(user_type="password", user_id="test_admin",
                            info={"password": make_password("test_admin")},
                            admin_p=True, institution=institution)
        self.admin = self.admin_client(admin,"test_admin")
        self.trustee = self.get_client()
        self.voter = self.get_client()
    
    def test_admin_created(self):
        admin = User.objects.get(user_id="test_admin")
        self.assertEqual(isinstance(admin,User) and admin.admin_p,True)
    def get_client(self):
        return Client()
    def admin_client(self, user, pwd):
        client = self.get_client()


        #why you no work?
        login_data = {'username': 'test_admin', 'password': 'test_admin'}
        r = client.post('/auth/auth/login', login_data)
        print r.content
        self.assertEqual(r.status_code, 302)
        r = client.post('/auth/auth/login', login_data, follow=True)
        self.assertRedirects(r, '/elections/new')

        wrong_data = {'username': 'wrong', 'password': 'wrong'}
        r = client.post('/auth/auth/login', wrong_data)
        self.assertEqual(r.status_code, 403)

        return client

    #def test_create_election(self,admin):
    #    pass
'''
