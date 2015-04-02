"""
Institution related urls
Shirlei Chaves (shirlei@gmail.com)

"""

from django.conf.urls import *


from views import *


urlpatterns = patterns('',
    (r'^manage_users$', manage_users),
    (r'^users$', users),
    (r'^(?P<role>[\w\ ]+)/delegate_user$', delegate_user),
    (r'^(?P<institution_id>\d+)/revoke_institution_admin$', revoke_institution_admin),
    (r'^(?P<institution_id>\d+)/revoke_election_admin$', revoke_election_admin),
)
