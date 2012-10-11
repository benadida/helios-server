from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from heliosauth.security import get_user
from helios.view_utils import render_template

def home(request):
  user = get_user(request)
  return render_template(request, "zeus/home", {'menu_active': 'home',
                                                        'user': user})

def faqs(request):
  user = get_user(request)
  return render_template(request, "zeus/faqs", {'menu_active': 'faqs',
                                                        'user': user})
