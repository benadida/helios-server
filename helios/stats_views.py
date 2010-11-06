"""
Helios stats views
"""

from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.http import *
from django.db import transaction

from security import *
from auth.security import get_user, save_in_session_across_logouts

def require_admin(request):
  user = get_user(request)
  if not user or not user.admin_p:
    raise PermissionDenied()

  return user

def home(request):
  return HttpResponse("foo")

def elections(request):
  user = require_admin(request)

  page = int(request.GET.get('page', 1))
  limit = int(request.GET.get('limit', 25))

  elections = Election.objects.all().order_by('-created_at')
  elections_paginator = Paginator(elections, limit)
  elections_page = elections_paginator.page(page)

  return render_template(request, "stats", {'elections' : elections_page.object_list, 'elections_page': elections_page,
                                            'limit' : limit})
    
