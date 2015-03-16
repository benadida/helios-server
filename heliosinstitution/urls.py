"""
Institution related urls
Shirlei Chaves (shirlei@gmail.com)

"""

from django.conf.urls import *


from views import *


urlpatterns = patterns('',
    (r'^manage_users$', manage_users),
    (r'^(?P<institution_id>\d+)/delegate_institution_admin$', delegate_institution_admin),
    (r'^(?P<institution_id>\d+)/revoke_institution_admin$', revoke_institution_admin),
    (r'^(?P<institution_id>\d+)/delegate_election_admin$', delegate_election_admin),
    (r'^(?P<institution_id>\d+)/revoke_election_admin$', revoke_election_admin),
)
