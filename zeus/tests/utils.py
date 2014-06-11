from django.test.client import Client
from django.contrib.auth.hashers import make_password

from helios.models import *
from heliosauth.models import User
from zeus.models import Institution


class SetUpAdminAndClientMixin():

    def setUp(self):
        self.institution = Institution.objects.create(name="test_inst")
        self.admin = User.objects.create(user_type="password",
                                         user_id="test_admin",
                                         info={"password": make_password("test_admin")},
                                         admin_p=True,
                                         institution=self.institution)
        self.locations = {'home': '/',
                          'logout': '/auth/auth/logout',
                          'login':'/auth/auth/login',
                          'create': '/elections/new'}
        self.login_data = {'username': 'test_admin', 'password': 'test_admin'}
        self.c = Client()

