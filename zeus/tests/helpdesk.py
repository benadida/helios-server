# -*- coding: utf-8 -*-
from django.test import TestCase
from django.contrib.auth.hashers import make_password
from django.utils import translation

from heliosauth.models import User
from zeus.models import Institution
from account_administration.forms import userForm

from utils import SetUpAdminAndClientMixin, get_messages_from_response


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
            institution=self.institution,
            )
        self.manager_creds = {
            'username': 'test_manager',
            'password': 'test_manager'
            }

        # create superadmin
        User.objects.create(
            user_type="password",
            user_id="test_superadmin",
            info={"password": make_password("test_superadmin")},
            superadmin_p=True,
            institution=self.institution,
            )
        self.superadmin_creds = {
            'username': 'test_superadmin',
            'password': 'test_superadmin',
            }

    # test user permissions

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

    def test_access_allowed_to_logged_superadmin(self):
        self.c.post(
            self.locations['login'],
            self.superadmin_creds,
            follow=True
            )
        r = self.c.get(self.locations['helpdesk'], follow=True)
        self.assertEqual(r.status_code, 200)

    def test_disabled_user_cannot_login(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_admin')
        u.is_disabled = True
        u.save()
        self.c.get(self.locations['logout'])
        r = self.c.post(
            self.locations['login'],
            self.login_data
            )
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = 'Ο λογαριασμός είναι απενεργοποιημένος'
        elif active_lang == 'en':
            asrt_message = 'Your account is disabled'
        asrt_message = asrt_message.decode('utf-8')
        self.assertFormError(
            r,
            'form',
            None,
            asrt_message,
            )
        r = self.c.get(self.locations['create'], follow=True)
        self.assertEqual(r.status_code, 403)

    # test user list view

    def test_user_list_view_returns_response(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/user_list/'
            )
        self.assertEqual(r.status_code, 200)

    def test_user_list_view_filters_users_with_user_id(self):
        filter_string = 'test'
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/user_list/'
            '?uid=%s' % filter_string
            )
        users = r.context['users']
        for u in users:
            self.assertTrue(filter_string in u.user_id)

    def test_user_list_view_filters_users_with_institution(self):
        filter_string = 'test'
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/user_list/'
            '?inst=%s' % filter_string
            )
        users = r.context['users']
        for u in users:
            self.assertTrue(filter_string in u.institution.name)

    def test_user_list_view_filters_users_with_uid_and_inst(self):
        filter_string = 'test'
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/user_list/'
            '?uid=%s'
            '&inst=%s'
            % (filter_string, filter_string)
            )
        users = r.context['users']
        for u in users:
            self.assertTrue(filter_string in u.user_id)
            self.assertTrue(filter_string in u.institution.name)

    # test manage user view

    def test_manage_view_returns_response(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/user_management/'
            )
        self.assertEqual(r.status_code, 200)

    def test_manage_view_error_message_if_no_user_or_wrong_id(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/user_management/'
            )
        messages = get_messages_from_response(r)
        error_message = messages[0].decode('utf-8')
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = "Δεν επιλέχθηκε χρήστης"
        elif active_lang == 'en':
            asrt_message = "You didn't choose a user"
        asrt_message = asrt_message.decode('utf-8')
        self.assertEqual(
            error_message,
            asrt_message
            )
        r = self.c.get(
            '/account_administration/user_management/'
            '?uid=765'
            )
        messages = get_messages_from_response(r)
        error_message = messages[0].decode('utf-8')
        self.assertEqual(
            error_message,
            asrt_message
            )

    def test_manage_view_returns_selected_user_data(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_admin')
        r = self.c.get(
            '/account_administration/user_management/'
            '?uid=%s' % u.id
            )
        context_user = r.context['u_data']
        self.assertEqual(context_user.id, u.id)

    def test_reset_password_asks_confirmation(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_admin')
        r = self.c.get(
            '/account_administration/reset_password/?uid=%s'
            % u.id,
            follow=True
            )

        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = "Παρακαλούμε επιβεβαιώστε την επανέκδοση"
        elif active_lang == 'en':
            asrt_message = "Please confirm the password reset"
        asrt_message = asrt_message.decode('utf-8')
        self.assertContains(
            r,
            asrt_message
            )

    def test_reset_password_confirmation_no_user(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/reset_password/',
            follow=True
            )
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = "Δεν επιλέχθηκε χρήστης"
        elif active_lang == 'en':
            asrt_message = "You didn't choose a user"
        asrt_message = asrt_message.decode('utf-8')
        self.assertContains(
            r,
            asrt_message
            )

    def test_manager_can_reset_admin_pass(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_admin')
        old_pass = u.info['password']
        self.c.get(
            '/account_administration'
            '/reset_password_confirmed/'
            '?uid=%s' % u.id
            )
        u = User.objects.get(user_id='test_admin')
        new_pass = u.info['password']
        self.assertNotEqual(old_pass, new_pass)

    def test_manager_cannot_reset_manager_and_superadmin_pass(self):
        user_ids = ['test_manager', 'test_superadmin']
        for user_id in user_ids:
            self.c.post(
                self.locations['login'],
                self.manager_creds,
                follow=True
                )
            u = User.objects.get(user_id=user_id)
            old_pass = u.info['password']
            r = self.c.get(
                '/account_administration'
                '/reset_password_confirmed/'
                '?uid=%s' % u.id,
                follow=True
                )
            u = User.objects.get(user_id=user_id)
            new_pass = u.info['password']
            self.assertEqual(old_pass, new_pass)
            messages = get_messages_from_response(r)
            error_message = messages[0].decode('utf-8')
            active_lang = translation.get_language()
            if active_lang == 'el':
                asrt_message = "Δεν επιτρέπεται αυτή η ενέργεια"
            elif active_lang == 'en':
                asrt_message = "You are not authorized to do this"
            asrt_message = asrt_message.decode('utf-8')
            self.assertEqual(
                error_message,
                asrt_message
                )

    def test_reset_password_of_nonexistent_user(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration'
            '/reset_password_confirmed/'
            '?uid=756',
            follow=True,
            )
        messages = get_messages_from_response(r)
        error_message = messages[0].decode('utf-8')
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = "Δεν επιλέχθηκε χρήστης"
        elif active_lang == 'en':
            asrt_message = "You didn't choose a user"
        asrt_message = asrt_message.decode('utf-8')
        self.assertEqual(
            error_message,
            asrt_message
            )

    def test_password_after_reset(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_admin')
        r = self.c.get(
            '/account_administration'
            '/reset_password_confirmed/'
            '?uid=%s' % u.id,
            follow=True
            )
        messages = get_messages_from_response(r)
        passw = messages[0].split(' ')[-1]

        self.c.get(self.locations['logout'])
        user = User.objects.get(user_id='test_admin')
        post_data = {
            'username': user.user_id,
            'password': passw
            }
        self.c.post(
            self.locations['login'],
            post_data
            )
        r = self.c.get(self.locations['create'], folow=True)
        self.assertEqual(r.status_code, 200)

    def test_disable_user(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_admin')
        uid = u.id
        post_data = {
            'user_id': 'test_admin',
            'institution': 'test_inst',
            'is_disabled': 'on',
            }
        self.c.post(
            '/account_administration/user_creation/?edit_id=%s'
            % uid,
            post_data,
            follow=True
            )
        u = User.objects.get(id=uid)
        self.assertTrue(u.is_disabled)

    def test_manager_cannot_disable_manager_or_superadmin(self):
        self.c.post(
            self.locations['login'],
            self.manager_creds,
            follow=True
            )
        user_ids = ['test_manager', 'test_superadmin']
        for user_id in user_ids:
            u = User.objects.get(user_id=user_id)
            uid = u.id
            post_data = {
                'user_id': u.user_id,
                'institution': u.institution.name,
                'is_disabled': 'on',
            }
            self.c.post(
                '/account_administration/user_creation/?edit_id=%s'
                % uid,
                post_data,
                follow=True
                )
            u = User.objects.get(user_id=user_id)
            self.assertFalse(u.is_disabled)

    def test_superadmin_can_disable_manager_or_superadmin(self):
        self.c.post(
            self.locations['login'],
            self.superadmin_creds,
            follow=True
            )
        user_ids = ['test_manager', 'test_superadmin']
        for user_id in user_ids:
            u = User.objects.get(user_id=user_id)
            uid = u.id
            post_data = {
                'user_id': u.user_id,
                'institution': u.institution.name,
                'is_disabled': 'on',
            }
            self.c.post(
                '/account_administration/user_creation/?edit_id=%s'
                % uid,
                post_data,
                follow=True
                )
            u = User.objects.get(user_id=user_id)
            self.assertTrue(u.is_disabled)

    # test create user view

    def test_create_user_form_errors(self):
        self.assertEqual(User.objects.all().count(), 3)
        self.c.post(self.locations['login'], self.manager_creds, follow=True)

        #post user withoud user_id
        post_data = {
            'user_id': '',
            'name': 'test_name',
            'institution': 'test_inst',
            }
        r = self.c.post(
            '/account_administration/user_creation/',
            post_data,
            folow=True
            )
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = 'Αυτό το πεδίο είναι απαραίτητο.'
        elif active_lang == 'en':
            asrt_message = 'This field is required.'
        asrt_message = asrt_message.decode('utf-8')
        self.assertEqual(User.objects.all().count(), 3)
        self.assertFormError(
            r,
            'form',
            'user_id',
            asrt_message,
            )
        post_data = {
            'user_id': 'a_user_id',
            'name': 'test_name',
            'institution': '',
            }
        r = self.c.post(
            '/account_administration/user_creation/',
            post_data,
            folow=True
            )
        self.assertEqual(User.objects.all().count(), 3)
        self.assertFormError(
            r,
            'form',
            'institution',
            asrt_message,
            )

    def test_create_user_with_nonexistent_institution(self):
        self.assertEqual(User.objects.all().count(), 3)
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        post_data = {
            'user_id': 'test_admin2',
            'institution': 'nonexistent_inst',
            }
        r = self.c.post(
            '/account_administration/user_creation/',
            post_data
            )
        self.assertEqual(User.objects.all().count(), 3)
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = ('Το Ίδρυμα δεν υπάρχει')
        elif active_lang == 'en':
            asrt_message = 'Institution does not exist'
        asrt_message = asrt_message.decode('utf-8')
        self.assertFormError(
            r,
            'form',
            'institution',
            asrt_message
            )

    def test_manager_can_create_user_with_post(self):
        # there are already 3 users
        self.assertEqual(User.objects.all().count(), 3)
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        post_data = {
            'user_id': 'new_test_user',
            'institution': 'test_inst'
            }
        self.c.post(
            '/account_administration/user_creation/',
            post_data
            )
        self.assertEqual(User.objects.all().count(), 4)

    def test_superadmin_can_create_user_with_post(self):
        # there are already 3 users
        self.assertEqual(User.objects.all().count(), 3)
        self.c.post(
            self.locations['login'],
            self.superadmin_creds,
            follow=True
            )
        post_data = {
            'user_id': 'new_test_user',
            'institution': 'test_inst'
            }
        self.c.post(
            '/account_administration/user_creation/',
            post_data
            )
        self.assertEqual(User.objects.all().count(), 4)

    def test_edit_user(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_admin')
        self.assertEqual(u.name, None)
        post_data = {
            'user_id': 'test_admin',
            'name': 'test_name',
            'institution': 'test_inst'
            }
        r = self.c.post(
            '/account_administration/user_creation/?edit_id=%s'
            % u.id,
            post_data,
            follow=True
            )
        u = User.objects.get(user_id='test_admin')
        self.assertEqual(u.name, 'test_name')
        messages = get_messages_from_response(r)
        message = messages[0].decode('utf-8')
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = 'Οι αλλαγές στον χρήστη αποθηκεύθηκαν επιτυχώς'
        elif active_lang == 'en':
            asrt_message = 'Changes on user were successfully saved'
        asrt_message = asrt_message.decode('utf-8')
        self.assertEqual(
            message,
            asrt_message
            )

    def test_create_user_form_filled_with_institution_from_get(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        inst = Institution.objects.get(name='test_inst')
        r = self.c.get(
            '/account_administration/user_creation/?id=%s'
            % inst.id,
            follow=True,
            )
        form = r.context['form']
        self.assertEqual(form['institution'].value(), 'test_inst')

    def test_create_user_already_exists(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        # we have 3 users in db
        self.assertEqual(User.objects.all().count(), 3)
        post_data = {
            'user_id': 'test_admin',
            'institution': 'test_inst'
            }
        r = self.c.post(
            '/account_administration/user_creation/',
            post_data,
            follow=True
            )
        self.assertEqual(User.objects.all().count(), 3)
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = 'Ο χρήστης υπάρχει ήδη!'
        elif active_lang == 'en':
            asrt_message = 'User already exists'
        asrt_message = asrt_message.decode('utf-8')
        self.assertFormError(
            r,
            'form',
            'user_id',
            asrt_message,
            )

    # test create institution view

    def test_create_institution_view_returns_response(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/institution_creation/',
            follow=True,
            )
        self.assertEqual(r.status_code, 200)

    def test_manager_can_create_institution_with_post(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        # before posting we must have only 1 institution
        self.assertEqual(Institution.objects.all().count(), 1)
        self.c.post(
            '/account_administration/institution_creation/',
            data={'name': 'new_test_inst'},
            follow=True
            )
        self.assertEqual(Institution.objects.all().count(), 2)

    def test_superadmin_can_create_institution_with_post(self):
        self.c.post(
            self.locations['login'],
            self.superadmin_creds,
            follow=True
            )
        # before posting we must have only 1 institution
        self.assertEqual(Institution.objects.all().count(), 1)
        self.c.post(
            '/account_administration/institution_creation/',
            data={'name': 'new_test_inst'},
            follow=True
            )
        self.assertEqual(Institution.objects.all().count(), 2)

    def test_create_institution_form_errors(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        # before posting we must have only 1 institution
        self.assertEqual(Institution.objects.all().count(), 1)
        r = self.c.post(
            '/account_administration/institution_creation/',
            data={'name': ''},
            follow=True
            )
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = 'Αυτό το πεδίο είναι απαραίτητο.'
        elif active_lang == 'en':
            asrt_message = 'This field is required.'
        asrt_message = asrt_message.decode('utf-8')
        self.assertEqual(Institution.objects.all().count(), 1)
        self.assertFormError(
            r,
            'form',
            'name',
            asrt_message,
            )

    def test_create_inst_already_exists(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        self.assertEqual(Institution.objects.all().count(), 1)
        post_data = {
            'name': 'test_inst'
            }
        r = self.c.post(
            '/account_administration/institution_creation/',
            post_data,
            follow=True
            )
        self.assertEqual(Institution.objects.all().count(), 1)
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = 'Το ίδρυμα υπάρχει ήδη'
        elif active_lang == 'en':
            asrt_message = 'Institution already exists'
        asrt_message = asrt_message.decode('utf-8')
        self.assertFormError(
            r,
            'form',
            'name',
            asrt_message,
            )



    def test_edit_institution(self):
        inst = Institution.objects.get(name='test_inst')
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        self.assertEqual(Institution.objects.all().count(), 1)
        post_data = {
            'name': 'edited_test_inst'
            }
        self.c.post(
            ('/account_administration/institution_creation/'
             '?id=%s' % inst.id),
            post_data,
            follow=True
            )
        self.assertEqual(Institution.objects.all().count(), 1)
        edited_inst = Institution.objects.get(id=inst.id)
        self.assertEqual(edited_inst.name, 'edited_test_inst')

    # test list institutions view

    def test_institution_list_view_returns_response(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/institution_list/'
            )
        self.assertEqual(r.status_code, 200)

    def test_institution_list_view_filtering(self):
        filter_string = 'test'
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/institution_list/'
            '?inst_name=%s' % filter_string
            )
        insts = r.context['institutions']
        for i in insts:
            self.assertTrue(filter_string in i.name)
