"""
Helios stats views
"""

import datetime

from django.core.paginator import Paginator
from django.urls import reverse
from django.db.models import Count, F, Max, Q
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django_tasks import TaskResultStatus
from django_tasks_db.models import DBTaskResult

from helios import tasks, url_names
from helios.management.commands.requeue_stuck_tasks import STUCK_AFTER_MINUTES
from helios.models import CastVote, Election
from helios_auth.models import User
from helios_auth.security import get_user, check_csrf
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

  now = timezone.now()
  task_counts = DBTaskResult.objects.aggregate(
    ready=Count('id', filter=Q(status=TaskResultStatus.READY)),
    running=Count('id', filter=Q(status=TaskResultStatus.RUNNING)),
    stuck=Count('id', filter=Q(status=TaskResultStatus.RUNNING,
                               started_at__lt=now - datetime.timedelta(minutes=STUCK_AFTER_MINUTES))),
    failed_last_day=Count('id', filter=Q(status=TaskResultStatus.FAILED,
                                         finished_at__gte=now - datetime.timedelta(days=1))))

  return render_template(request, 'stats', {'num_votes_in_queue': num_votes_in_queue, 'task_counts': task_counts,
                                            'stuck_after_minutes': STUCK_AFTER_MINUTES})

def force_queue(request):
  user = require_admin(request)
  check_csrf(request)

  votes_in_queue = CastVote.objects.filter(invalidated_at=None, verified_at=None)
  for cv in votes_in_queue:
    tasks.cast_vote_verify_and_store.enqueue(cv.id)

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
  cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=1)
  elections_with_votes_in_24hours = CastVote.objects.filter(
    cast_at__gt=cutoff, voter__election__deleted_at=None
  ).values(
    election_id=F('voter__election'), uuid=F('voter__election__uuid'), name=F('voter__election__name')
  ).annotate(
    last_cast_vote=Max('cast_at'), num_recent_cast_votes=Count('id')
  ).order_by('-last_cast_vote')

  return render_template(request, "stats_recent_votes", {'elections' : elections_with_votes_in_24hours})

def recent_problem_elections(request):
  user = require_admin(request)

  # elections left unfrozen older than 1 day old (and younger than 10 days old, so we don't go back too far)
  elections_with_problems = Election.objects.filter(frozen_at = None, created_at__gt = datetime.datetime.utcnow() - datetime.timedelta(days=10), created_at__lt = datetime.datetime.utcnow() - datetime.timedelta(days=1) )

  return render_template(request, "stats_problem_elections", {'elections' : elections_with_problems})

def user_search(request):
  user = require_admin(request)

  q = request.GET.get('q', '')
  found_users = []

  if q:
    # Search for users by name, user_id, or email (in info field)
    from django.db.models import Q
    found_users = User.objects.filter(
      Q(name__icontains=q) |
      Q(user_id__icontains=q)
    ).order_by('name')

  # For each user, get their elections
  users_with_elections = []
  for found_user in found_users:
    # Get elections where user is admin (creator or additional admin)
    elections_as_admin = Election.get_by_user_as_admin(found_user)

    # Get elections where user is a voter
    elections_as_voter = Election.get_by_user_as_voter(found_user)

    # Get elections where user is a trustee (by email matching user_id)
    elections_as_trustee = Election.objects.filter(
      trustee__email__iexact=found_user.user_id
    ).distinct()

    users_with_elections.append({
      'user': found_user,
      'elections_as_admin': elections_as_admin,
      'elections_as_voter': elections_as_voter,
      'elections_as_trustee': elections_as_trustee,
    })

  return render_template(request, "stats_user_search", {
    'q': q,
    'users_with_elections': users_with_elections
  })

def deleted_elections(request):
  user = require_admin(request)

  page = int(request.GET.get('page', 1))
  limit = int(request.GET.get('limit', 25))
  q = request.GET.get('q','')

  # Get deleted elections, searching by name if query provided
  elections_query = Election.objects_with_deleted.filter(deleted_at__isnull=False)
  if q:
    elections_query = elections_query.filter(name__icontains=q)

  elections = elections_query.order_by('-deleted_at')
  elections_paginator = Paginator(elections, limit)
  elections_page = elections_paginator.page(page)

  total_elections = elections_paginator.count

  return render_template(request, "stats_deleted_elections", {
    'elections': elections_page.object_list,
    'elections_page': elections_page,
    'limit': limit,
    'total_elections': total_elections,
    'q': q
  })

@require_http_methods(["POST"])
def undelete_election(request, election_uuid):
  user = require_admin(request)
  check_csrf(request)

  # Get the deleted election
  election = Election.objects_with_deleted.get(uuid=election_uuid)

  if not election or not election.is_deleted:
    raise PermissionDenied()

  # Undelete it
  election.undelete()

  # Redirect back to deleted elections list
  return HttpResponseRedirect(reverse(url_names.stats.STATS_DELETED_ELECTIONS))
