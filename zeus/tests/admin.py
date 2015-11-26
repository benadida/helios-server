from django.test import TestCase
from django.core.urlresolvers import reverse

from zeus.tests.utils import SetUpAdminAndClientMixin
from helios.models import Election

class TestHomeView(SetUpAdminAndClientMixin, TestCase):

    def setUp(self):
        super(TestHomeView, self).setUp()

    def login(self):
        self.c.post(self.locations['login'], self.login_data)

    def create_election(self):
        self.election_form['departments'] = 'test_departments'
        self.election_form['election_module'] = 'simple'
        self.c.post(self.locations['create'], self.election_form, follow=True)

        return Election.objects.all()[0]

    def post_and_get_response(self):
        """
        Create an election and post on admin_home
        to change their official status.
        """
        election = self.create_election()
        return self.c.post(
            reverse('admin_home'),
            {
                'official': [1],
                'uuid': [election.uuid]
            }
        )
        
    def test_post_without_login(self):
        """
        If someone tries to do a POST request on admin_home
        without having logged in the view should respond
        with a 403(Permission Denied) HTTP code.
        """
        response = self.c.post(
            reverse('admin_home'),
            {}
        )

        self.assertEqual(response.status_code, 403)

    def test_post_without_superadmin(self):
        """
        If someone tries to do a POST request on admin_home
        without having superadmin access the view should
        respond with a 403(Permission Denied) HTTP code.
        """
        self.login()

        response = self.post_and_get_response()

        self.assertEqual(response.status_code, 403)

    def test_post_with_superadmin(self):
        """
        If someone tries to do a POST request on admin_home
        with superadmin access the view should
        respond with a 302(Redirection) HTTP code.
        """
        self.admin.superadmin_p = True
        self.admin.save()

        self.login()

        response = self.post_and_get_response()

        self.assertEqual(response.status_code, 302)

    def test_get_without_superadmin(self):
        """
        If someone does a GET request on admin_home
        without superadmin access the template 
        returned should not contain a form.
        """
        self.login()
        election = self.create_election()

        response = self.c.get(
            reverse('admin_home'),
            {}
        )

        self.assertNotContains(response, '<select name="official">')

    def test_get_with_superadmin(self):
        """
        If someone does a GET request on admin_home
        with superadmin access the template 
        returned should contain a form.
        """
        self.admin.superadmin_p = True
        self.admin.save()

        self.login()
        election = self.create_election()

        response = self.c.get(
            reverse('admin_home'),
            {}
        )

        self.assertContains(response, '</form>')
        self.assertContains(response, '<select name="official">')
        self.assertContains(response, '<input type="submit"')
        self.assertContains(response, '<input type="hidden"')
