"""
Institution related urls
Shirlei Chaves (shirlei@gmail.com)

"""

from django.conf.urls import url

import url_names
from views import *

urlpatterns = [
    url(r'^$', home, name=url_names.INSTITUTION_INDEX),
    url(r'^dashboard$', dashboard, name=url_names.INSTITUTION_DASHBOARD),
    url(r'^stats$', stats, name=url_names.INSTITUTION_STATS),
    url(r'^manage_users$', manage_users, name=url_names.INSTITUTION_USERS_MANAGE),
    url(r'^users$', users, name=url_names.INSTITUTION_USERS),
    url(r'^admin-actions$', admin_actions, name=url_names.INSTITUTION_ADMIN_ACTIONS),
    url(r'^(?P<institution_pk>\d+)/elections/(?P<type>\w+)/(?P<year>\d{4})?$',
        elections_by_type_year, name=url_names.INSTITUTION_ELECTIONS_TYPE_YEAR),
    url(r'^(?P<institution_pk>\d+)/details$', institution_details, name=url_names.INSTITUTION_DETAILS),
    url(r'^elections/(?P<year>\d{4})?$', elections_by_year, name=url_names.INSTITUTION_ELECTIONS_YEAR),
    url(r'^elections/summary/(?P<year>\d{4})?$', elections_summary, name=url_names.INSTITUTION_ELECTIONS_SUMMARY),
    url(r'^(?P<role>[\w\ ]+)/delegate_user$', delegate_user, name=url_names.INSTITUTION_USER_DELEGATE),
    url(r'^(?P<user_pk>\d+)/revoke_user$', revoke_user, name=url_names.INSTITUTION_USER_REVOKE),
    url(r'^(?P<user_pk>\d+)/user_metadata$', user_metadata, name=url_names.INSTITUTION_USER_METADATA),
    url(r'^(?P<user_pk>\d+)/add_expires_at$', add_expires_at, name=url_names.INSTITUTION_USER_ADD_EXPIRES),
    url(r'^users/(?P<user_pk>\d+)/elections/administered$', elections_administered,
        name=url_names.INSTITUTION_USER_ADMINISTERED_ELECTIONS),
]
