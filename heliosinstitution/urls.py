"""
Institution related urls
Shirlei Chaves (shirlei@gmail.com)

"""

from django.conf.urls import *


from views import *


urlpatterns = patterns('',
    (r'^manage_users$', manage_users),
)
