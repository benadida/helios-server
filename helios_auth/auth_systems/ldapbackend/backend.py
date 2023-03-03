"""
LDAP Authentication
Author : shirlei@gmail.com
Version: 1.0
Requires:
- libldap2-dev
- django-auth-ldap 1.2.6
Technical support from IFSC - Instituto Federal de Santa Catarina
http://dtic.ifsc.edu.br/sistemas/sistema-de-votacao-on-line-helios/
"""

from django.core.exceptions import ImproperlyConfigured

from django_auth_ldap.backend import LDAPBackend


class CustomLDAPBackend(LDAPBackend):

    def authenticate_ldap_user(self, username, password):
        """
        Some ldap servers allow anonymous search but naturally return just a set of user attributes. So, here we re-perform search and populate user methods. For now, just in cases where AUTH_LDAP_BIND_PASSWORD is empty
        """
        user =  super(CustomLDAPBackend, self).authenticate_ldap_user(username, password)

        if user and self.settings.BIND_PASSWORD == '' :
            search = self.settings.USER_SEARCH
            if not isinstance(search, LDAPSearch):
                raise ImproperlyConfigured('AUTH_LDAP_USER_SEARCH must be an LDAPSearch instance.')
            results = search.execute(user.ldap_user.connection, {'user': user.username})
            if results is not None and len(results) == 1:
                (user.ldap_user._user_dn, user.ldap_user.user_attrs) = results[0]
                user.ldap_user._load_user_attrs()
                user.ldap_user._populate_user_from_attributes()
                user.save()
        return user
