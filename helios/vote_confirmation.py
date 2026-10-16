"""Durable confirmation delivery, independent of vote acceptance and the browser."""
import datetime
import uuid
import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from helios_auth.bridge_protocol import https_origin
from .models import VoteConfirmationEmail


def queue_confirmation(cast):
    from .bridge_eligibility import bridge_election
    voter = cast.voter
    if not voter.user or voter.user.user_type != 'alu' or not bridge_election(voter.election):
        return
    VoteConfirmationEmail.objects.get_or_create(cast_vote=cast, defaults={'payload': {
        'recipient': voter.user.info['email'].lower(),
        'election_id': voter.election.uuid,
        'election_name': voter.election.name,
    }})


def deliver_next_confirmation():
    now = datetime.datetime.utcnow()
    with transaction.atomic():
        job = (VoteConfirmationEmail.objects.select_for_update(skip_locked=True)
            .filter(next_attempt_at__lte=now)
            .filter(Q(state='pending') | Q(state='sending', attempted_at__lt=now-datetime.timedelta(minutes=2)))
            .order_by('next_attempt_at', 'id').first())
        if not job:
            return False
        if job.first_attempt_at and job.first_attempt_at < now-datetime.timedelta(hours=23):
            job.state = 'review_required'
            job.save(update_fields=['state'])
            return True
        job.state = 'sending'
        job.attempts += 1
        job.first_attempt_at = job.first_attempt_at or now
        job.attempted_at = now
        job.lease = uuid.uuid4()
        job.save()
    # No ballot, proof, tracker, subject ID or candidate choices enter this call.
    delivered = False
    try:
        response = requests.post(https_origin(settings.ALU_BRIDGE_APP_ORIGIN) + '/api/helios/vote-email',
            headers={'Authorization': 'Bearer ' + settings.ALU_BRIDGE_SECRET},
            json={'id': str(job.id), **job.payload}, timeout=15, allow_redirects=False)
        delivered = response.status_code == 200 and response.json().get('sent') is True
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        pass
    VoteConfirmationEmail.objects.filter(id=job.id, state='sending', lease=job.lease).update(
        state='sent' if delivered else 'pending',
        sent_at=datetime.datetime.utcnow() if delivered else None,
        next_attempt_at=datetime.datetime.utcnow()+datetime.timedelta(seconds=min(300, 5*2**min(job.attempts, 6))))
    return True
