"""
Helios stats views
"""

import datetime

from django.core.paginator import Paginator
from django.urls import reverse
from django.db.models import Max, Count
from django.http import HttpResponseRedirect

from helios import tasks, url_names
from helios.models import CastVote, Election
from helios_auth.security import get_user
from .security import PermissionDenied
from .view_utils import render_template


def require_admin(request):
  user = get_user(request)
  if not user or not user.admin_p:
    raise PermissionDenied()

  return user

def home(request):
  user = require_admin(request)
  num_votes_in_queue = CastVote.objects.filter(invalidated_at=None, verified_at=None).count()
  return render_template(request, 'stats', {'num_votes_in_queue': num_votes_in_queue})

def force_queue(request):
  user = require_admin(request)
  votes_in_queue = CastVote.objects.filter(invalidated_at=None, verified_at=None)
  for cv in votes_in_queue:
    tasks.cast_vote_verify_and_store.delay(cv.id)

  return HttpResponseRedirect(reverse(url_names.stats.STATS_HOME))

def elections(request):
  user = require_admin(request)

  page = int(request.GET.get('page', 1))
  limit = int(request.GET.get('limit', 25))
  q = request.GET.get('q','')

  elections = Election.objects.filter(name__icontains = q).order_by('-created_at')
  elections_paginator = Paginator(elections, limit)
  elections_page = elections_paginator.page(page)

  total_elections = elections_paginator.count

  return render_template(request, "stats_elections", {'elections' : elections_page.object_list, 'elections_page': elections_page,
                                                      'limit' : limit, 'total_elections': total_elections, 'q': q})
    
def recent_votes(request):
  user = require_admin(request)
  
  # elections with a vote in the last 24 hours, ordered by most recent cast vote time
  # also annotated with number of votes cast in last 24 hours
  elections_with_votes_in_24hours = Election.objects.filter(voter__castvote__cast_at__gt= datetime.datetime.utcnow() - datetime.timedelta(days=1)).annotate(last_cast_vote = Max('voter__castvote__cast_at'), num_recent_cast_votes = Count('voter__castvote')).order_by('-last_cast_vote')

  return render_template(request, "stats_recent_votes", {'elections' : elections_with_votes_in_24hours})

def recent_problem_elections(request):
  user = require_admin(request)

  # elections left unfrozen older than 1 day old (and younger than 10 days old, so we don't go back too far)
  elections_with_problems = Election.objects.filter(frozen_at = None, created_at__gt = datetime.datetime.utcnow() - datetime.timedelta(days=10), created_at__lt = datetime.datetime.utcnow() - datetime.timedelta(days=1) )

  return render_template(request, "stats_problem_elections", {'elections' : elections_with_problems})
