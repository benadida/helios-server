from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from heliosauth.security import get_user
from helios.view_utils import render_template

def home(request):
  user = get_user(request)
  return render_template(request, "zeus/home", {'menu_active': 'home',
                                                        'user': user})

def faqs_trustee(request):
  user = get_user(request)
  return render_template(request, "zeus/faqs_admin", {'menu_active': 'faqs',
                                                      'submenu': 'admin', 'user': user})
def faqs_voter(request):
  user = get_user(request)
  return render_template(request, "zeus/faqs_voter", {'menu_active': 'faqs',
                                                      'submenu': 'voter',
                                                        'user': user})
def resources(request):
  user = get_user(request)
  return render_template(request, "zeus/resources", {'menu_active': 'resources',
                                                     'user': user})
