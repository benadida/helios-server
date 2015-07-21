"""
Institution related urls
Shirlei Chaves (shirlei@gmail.com)

"""

from django.conf.urls import *


from views import *


urlpatterns = patterns('',
	(r'^$', home),
	(r'^dashboard$', dashboard),
	(r'^stats$', stats),
	(r'^manage_users$', manage_users),
	(r'^users$', users),
	(r'^admin-actions$', admin_actions),
	(r'^(?P<institution_pk>\d+)/elections/(?P<type>\w+)/(?P<year>\d{4})?$', 
		elections_by_type_year),
	(r'^(?P<institution_pk>\d+)/details$', institution_details),
	(r'^elections/(?P<year>\d{4})?$', elections_by_year),
	(r'^elections/summary/(?P<year>\d{4})?$', elections_summary),	
	(r'^(?P<role>[\w\ ]+)/delegate_user$', delegate_user),
	(r'^(?P<user_pk>\d+)/revoke_user$', revoke_user),
	(r'^(?P<user_pk>\d+)/user_metadata$', user_metadata),
)
