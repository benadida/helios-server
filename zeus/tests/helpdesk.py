# -*- coding: utf-8 -*-

import datetime
from datetime import timedelta

from django.test import TestCase
from django.contrib.auth.hashers import make_password
from django.utils import translation

from heliosauth.models import User
from zeus.models import Institution

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
        self.c.post(self.locations['login'], self.superadmin_creds, follow=True)
        # before posting we must have only 1 institution
        self.assertEqual(Institution.objects.all().count(), 1)
        self.c.post(
            '/account_administration/institution_creation/',
           data={'name': 'new_test_inst'},
           follow=True
            )
        self.assertEqual(Institution.objects.all().count(), 2)

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
        self.c.post(self.locations['login'], self.superadmin_creds, follow=True)
        post_data = {
            'user_id': 'new_test_user',
            'institution': 'test_inst'
            }
        self.c.post(
            '/account_administration/user_creation/',
            post_data
            )
        self.assertEqual(User.objects.all().count(), 4)

    def test_manager_can_delete_institution(self):
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

    def test_delete_institution_that_does_not_exit(self):
        inst_id = 675
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/inst_deletion_confirmed/?id=%s'
                % inst_id,
            follow=True
            )
        messages = get_messages_from_response(r)
        error_message = messages[0].decode('utf-8')
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = 'Αυτό το ίδρυμα δεν υπάρχει.'
        elif active_lang == 'en':
            asrt_message = 'No such institution'
        asrt_message = asrt_message.decode('utf-8')
        self.assertEqual(
            error_message,
            asrt_message
            )

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
        # admin test_admin has test_inst as institution
        self.c.post(self.locations['login'], self.login_data)
        self.c.post(self.locations['create'], election_form) 
        u = User.objects.get(user_id='test_admin')
        self.assertEqual(u.elections.count(), 1)
        self.c.get(self.locations['logout'])

        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        inst = Institution.objects.get(name='test_inst')
        inst_id = inst.id
        self.c.get(
            '/account_administration/inst_deletion_confirmed/?id=%s'\
                % inst_id
            )
        inst = Institution.objects.get(name='test_inst')
        self.assertEqual(inst.is_disabled, False)


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

    def test_disabled_user_cannot_login(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        # current admin user has no elections and can be deleted
        u = User.objects.get(user_id='test_admin')
        u_id = u.id
        self.c.get(
            '/account_administration/user_deletion_confirmed/?id=%s'\
                % u_id
            )
        self.c.get(self.locations['logout'])
        active_lang = translation.get_language()
        if active_lang == 'el':
           assert_string = 'απενεργοποιημένος' 
        elif active_lang == 'en':
           assert_string = 'disabled' 
        r = self.c.post(self.locations['login'], self.login_data)
        self.assertIn(assert_string, r.content)
        r = self.c.get(self.locations['create'], follow=True)
        self.assertEqual(r.status_code, 403)

    def test_manager_can_reset_admin_pass(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_admin')
        old_pass = u.info['password']
        self.c.get(
            '/account_administration'
            '/reset_password_confirmed/'
            '?user_id_filter=%s' % u.id
            )
        u = User.objects.get(user_id='test_admin')
        new_pass = u.info['password']
        self.assertNotEqual(old_pass, new_pass)

    def test_manager_cannot_reset_manager_pass(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_manager')
        old_pass = u.info['password']
        self.c.get(
            '/account_administration'
            '/reset_password_confirmed/'
            '?user_id_filter=%s' % u.id
            )
        u = User.objects.get(user_id='test_manager')
        new_pass = u.info['password']
        self.assertEqual(old_pass, new_pass)
    
    def test_manager_cannot_reset_superadmin_pass(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_superadmin')
        old_pass = u.info['password']
        self.c.get(
            '/account_administration'
            '/reset_password_confirmed/'
            '?user_id_filter=%s' % u.id
            )
        u = User.objects.get(user_id='test_superadmin')
        new_pass = u.info['password']
        self.assertEqual(old_pass, new_pass)

    def test_reset_password_of_nonexistent_user(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration'
            '/reset_password_confirmed/'
            '?user_id_filter=756',
            follow=True,
            )
        messages = get_messages_from_response(r)
        error_message =  messages[0].decode('utf-8')
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

    def test_manager_cannot_disable_manager_or_superadmin(self):
        user_ids = ['test_manager', 'test_superadmin']
        for user_id in user_ids:
            self.c.post(self.locations['login'], self.manager_creds, follow=True)
            u = User.objects.get(user_id=user_id)
            u_id = u.id
            r = self.c.get(
                '/account_administration/user_deletion_confirmed/?id=%s'\
                    % u_id,
                follow=True
                )
            u = User.objects.get(user_id=user_id)
            self.assertFalse(u.is_disabled)
            messages = get_messages_from_response(r)
            error_message =  messages[0].decode('utf-8')
            active_lang = translation.get_language()
            if active_lang == 'el':
                asrt_message = 'Δεν επιτρέπεται να διαγράψετε αυτόν τον χρήστη'
            elif active_lang == 'en':
                asrt_message = 'You are not authorized to delete that user'
            asrt_message = asrt_message.decode('utf-8')
            self.assertEqual(
                error_message,
                asrt_message
                ) 
    def test_superadmin_can_disable_manager_or_superadmin(self):
        user_ids = ['test_manager', 'test_superadmin']
        for user_id in user_ids:
            self.c.post(self.locations['login'], self.superadmin_creds, follow=True)
            u = User.objects.get(user_id=user_id)
            u_id = u.id
            r = self.c.get(
                '/account_administration/user_deletion_confirmed/?id=%s'\
                    % u_id,
                follow=True
                )
            u = User.objects.get(user_id=user_id)
            self.assertTrue(u.is_disabled)
            messages = get_messages_from_response(r)
            error_message =  messages[0].decode('utf-8')
            active_lang = translation.get_language()
            if active_lang == 'el':
                asrt_message = 'Ο χρήστης %s διαγράφηκε επιτυχώς!' % user_id
            elif active_lang == 'en':
                asrt_message = 'User %s succesfuly deleted!' %user_id
            asrt_message = asrt_message.decode('utf-8')
            self.assertEqual(
                error_message,
                asrt_message
                ) 

    def test_disable_user_that_does_not_exist(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/user_deletion_confirmed/?id=756',
            follow=True,
            )
        messages = get_messages_from_response(r)
        error_message =  messages[0].decode('utf-8')
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = 'Δεν επιλέχθηκε χρήστης'
        elif active_lang == 'en':
            asrt_message = "You didn't choose a user"
        asrt_message = asrt_message.decode('utf-8')
        self.assertEqual(
            error_message,
            asrt_message
            )

    def test_superamdin_can_reset_admin_pass(self):
        self.c.post(self.locations['login'], self.superadmin_creds, follow=True)
        u = User.objects.get(user_id='test_admin')
        old_pass = u.info['password']
        self.c.get(
            '/account_administration'
            '/reset_password_confirmed/'
            '?user_id_filter=%s' % u.id
            )
        u = User.objects.get(user_id='test_admin')
        new_pass = u.info['password']
        self.assertNotEqual(old_pass, new_pass)

    def test_superadmin_can_reset_manager_pass(self):
        self.c.post(self.locations['login'], self.superadmin_creds, follow=True)
        u = User.objects.get(user_id='test_manager')
        old_pass = u.info['password']
        self.c.get(
            '/account_administration'
            '/reset_password_confirmed/'
            '?user_id_filter=%s' % u.id
            )
        u = User.objects.get(user_id='test_manager')
        new_pass = u.info['password']
        self.assertNotEqual(old_pass, new_pass)

    def test_superadmin_can_reset_superadmin_pass(self):
        self.c.post(self.locations['login'], self.superadmin_creds, follow=True)
        u = User.objects.get(user_id='test_superadmin')
        old_pass = u.info['password']
        self.c.get(
            '/account_administration'
            '/reset_password_confirmed/'
            '?user_id_filter=%s' % u.id
            )
        u = User.objects.get(user_id='test_superadmin')
        new_pass = u.info['password']
        self.assertNotEqual(old_pass, new_pass)

    def test_password_after_reset(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_admin')
        old_pass = u.info['password']
        r = self.c.get(
            '/account_administration'
            '/reset_password_confirmed/'
            '?user_id_filter=%s' % u.id,
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
    
    def test_create_inst_that_exists_and_is_disabled(self):
        # test both when exists and when exists and is disabled
        inst = Institution.objects.create(
            name='test_exists',
            )
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        self.assertEqual(Institution.objects.all().count(), 2)
        r = self.c.post(
            '/account_administration/institution_creation/',
           data={'name': 'test_exists'},
           follow=True
           )
        self.assertEqual(Institution.objects.all().count(), 2)
        form = r.context['form']
        error_message = form.errors['name'][0]
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = 'Το ίδρυμα υπάρχει ήδη'
        elif active_lang == 'en':
            asrt_message = 'Institution already exists'
        asrt_message = asrt_message.decode('utf-8')
        self.assertEqual(
            error_message,
            asrt_message
            )
        inst.is_disabled = True
        inst.save()
        r = self.c.post(
            '/account_administration/institution_creation/',
            data={'name': 'test_exists'},
            follow=True,
            )
        self.assertEqual(Institution.objects.all().count(), 2)
        form = r.context['form']
        error_message = form.errors['name'][0]
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = 'Το ίδρυμα υπάρχει ήδη και είναι απενεργοποιημένο'
        elif active_lang == 'en':
            asrt_message = 'Institution already exists and it is disabled'
        asrt_message = asrt_message.decode('utf-8')
        self.assertEqual(
            error_message,
            asrt_message
            ) 

    def test_create_user_with_disabled_inst(self):
        # current users are 3
        self.assertEqual(User.objects.all().count(), 3)
        inst = Institution.objects.create(name='disabled', is_disabled=True)
        self.assertEqual(inst.is_disabled, True)
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        post_data = {
            'user_id': 'test_admin2',
            'institution': inst.name,
            }
        r = self.c.post(
            '/account_administration/user_creation/',
            post_data
            ) 
        self.assertEqual(User.objects.all().count(), 3)
        form = r.context['form']
        error_message = form.errors['institution'][0]
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = ('Το ίδρυμα έχει απενεργοποιηθεί'
                            ' και δεν μπορεί να χρησιμοποιηθεί.')
        elif active_lang == 'en':
            asrt_message = 'Institution is disabled and cannot be used'
        asrt_message = asrt_message.decode('utf-8')
        self.assertEqual(
            error_message,
            asrt_message
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
        form = r.context['form']
        error_message = form.errors['institution'][0]
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = ('Το Ίδρυμα δεν υπάρχει')
        elif active_lang == 'en':
            asrt_message = 'Institution does not exist'
        asrt_message = asrt_message.decode('utf-8')
        self.assertEqual(
            error_message,
            asrt_message
            ) 
    
    def test_request_user_to_be_deleted_asks_confirmation(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_admin')
        r = self.c.get(
            '/account_administration/delete_user?id=%s' % u.id,
            follow=True
            )
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = ('Παρακαλώ επιβεβαιώστε την διαγραφή του χρήστη')
        elif active_lang == 'en':
            asrt_message = 'Please confirm the deletion of user'
        asrt_message = asrt_message.decode('utf-8')
        context_user = r.context['user_for_deletion']
        self.assertEqual(u.id, context_user.id)
        self.assertContains(
            r,
            asrt_message,
            status_code=200
            )
        self.assertContains(
            r,
            '/account_administration/user_deletion_confirmed/?id=%s'\
                % u.id,
             status_code=200
             )

    def test_request_nonexistent_user_to_be_deleted(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/delete_user?id=756',
            follow=True
            )
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = ('Δεν επιλέχθηκε χρήστης.')
        elif active_lang == 'en':
            asrt_message = "You didn't choose a user."
        asrt_message = asrt_message.decode('utf-8')
        context_user = r.context['user_for_deletion']
        self.assertEqual(None, context_user)
        self.assertContains(
            r,
            asrt_message,
            status_code=200
            )

    def test_request_inst_to_be_deleted_asks_confirmation(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        inst = Institution.objects.get(name='test_inst')
        r = self.c.get(
            '/account_administration/delete_institution?id=%s' % inst.id,
            follow=True
            )
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = 'Παρακαλώ επιβεβαιώστε την διαγραφή του ιδρύματος'
        elif active_lang == 'en':
            asrt_message = 'Please confirm the deletion of institution'
        asrt_message = asrt_message.decode('utf-8')
        context_inst = r.context['inst']
        self.assertEqual(inst.id, context_inst.id)
        self.assertContains(
            r,
            asrt_message,
            status_code=200
            )
        self.assertContains(
            r,
            '/account_administration/inst_deletion_confirmed/?id=%s'\
                % inst.id,
             status_code=200
             )

    def test_request_nonexistent_inst_to_be_deleted(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/delete_institution?id=756',
            follow=True
            )
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = ('Δεν επιλέχθηκε ίδρυμα.')
        elif active_lang == 'en':
            asrt_message = "You didn't choose an institution."
        asrt_message = asrt_message.decode('utf-8')
        context_inst = r.context['inst']
        self.assertEqual(None, context_inst)
        self.assertContains(
            r,
            asrt_message,
            status_code=200
            )

    def test_request_for_passw_reset(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        u = User.objects.get(user_id='test_admin')
        r = self.c.get(
            '/account_administration/reset_password?user_id_filter=%s' % u.id,
            follow=True
            )
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = ('Παρακαλούμε επιβεβαιώστε την επανέκδοση του'
                            ' κωδικού του του χρήστη')
        elif active_lang == 'en':
            asrt_message = 'Please confirm the password reset of user'
        asrt_message = asrt_message.decode('utf-8')
        context_user = r.context['u_data']
        self.assertEqual(u.id, context_user.id)
        self.assertContains(
            r,
            asrt_message,
            status_code=200
            )
        self.assertContains(
            r,
            ('/account_administration/reset_password_confirmed/'
             '?user_id_filter=%s' % u.id),
             status_code=200
             )

    def test_request_for_passw_reset_of_nonexistent_user(self):
        self.c.post(self.locations['login'], self.manager_creds, follow=True)
        r = self.c.get(
            '/account_administration/reset_password?user_id_filter=756',
            follow=True,
            )
        active_lang = translation.get_language()
        if active_lang == 'el':
            asrt_message = "Δεν επιλέχθηκε χρήστης."
        elif active_lang == 'en':
            asrt_message = "You didn't choose a user."
        asrt_message = asrt_message.decode('utf-8')
        context_user = r.context['u_data']
        self.assertEqual(None, context_user)
        self.assertContains(
            r,
            asrt_message,
            status_code=200
            )
