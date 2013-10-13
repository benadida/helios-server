from django.conf.urls.defaults import *

urlpatterns = patterns('{{ project }}.{{ app }}.views',
    (r'^$', 'canvas'),
    # Define other pages you want to create here
)

