"""PostgreSQL-backed verification queue, independent of a hosting provider."""
import datetime
import logging

from django.conf import settings
from django.db import connection, transaction
from django.db.models import F, Q

from .models import CastVote, VoteVerificationJob

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 8


def database_queue_enabled():
    return settings.ALU_VOTE_VERIFICATION_BACKEND == 'database'


def schedule_verification(cast_vote):
    """Call inside the same atomic block that saves the accepted CastVote."""
    if not connection.in_atomic_block:
        raise RuntimeError('Vote acceptance and verification scheduling must be atomic.')
    if not database_queue_enabled():
        raise RuntimeError('Database verification is not enabled.')
    VoteVerificationJob.objects.get_or_create(cast_vote_id=cast_vote.pk)


def recover_pending_jobs():
    """Backfill pre-queue interruptions at worker startup; read IDs only."""
    candidates = (CastVote.objects.filter(invalidated_at=None,
        verification_job__isnull=True, voter__election__deleted_at=None)
        .filter(Q(verified_at=None) | Q(voter__cast_at=None) | Q(cast_at__gt=F('voter__cast_at')))
        .filter(Q(quarantined_p=False) | Q(released_from_quarantine_at__isnull=False))
        .values_list('pk', flat=True).iterator(chunk_size=500))
    batch = []
    for pk in candidates:
        batch.append(VoteVerificationJob(cast_vote_id=pk))
        if len(batch) == 500:
            VoteVerificationJob.objects.bulk_create(batch, ignore_conflicts=True)
            batch = []
    if batch:
        VoteVerificationJob.objects.bulk_create(batch, ignore_conflicts=True)


def process_next_job():
    """Claim one due job. PostgreSQL releases its lock after a crash.

    Separate workers skip locked jobs. No lease in memory, duplicate ciphertext,
    or network enqueue is needed. Verification and job completion commit once.
    """
    if not connection.features.has_select_for_update_skip_locked:
        raise RuntimeError('The database verification worker requires PostgreSQL row locking.')
    from .tasks import cast_vote_verify_and_store
    with transaction.atomic():
        job = (VoteVerificationJob.objects.select_for_update(skip_locked=True, of=('self',))
            .filter(state='pending', next_attempt_at__lte=datetime.datetime.utcnow())
            .filter(Q(cast_vote__quarantined_p=False) |
                    Q(cast_vote__released_from_quarantine_at__isnull=False))
            .filter(cast_vote__voter__election__deleted_at=None)
            .order_by('next_attempt_at', 'pk').first())
        if job is None:
            return False
        job.attempts += 1
        try:
            # An unexpected verification/store exception rolls back the entire
            # attempt, while leaving the outer transaction usable for retry data.
            with transaction.atomic():
                cast_vote_verify_and_store(job.cast_vote_id)
        except Exception as exc:
            job.last_error_code = type(exc).__name__[:80]
            if job.attempts >= MAX_ATTEMPTS:
                job.state = 'failed'
            else:
                job.next_attempt_at = datetime.datetime.utcnow() + datetime.timedelta(
                    seconds=min(300, 5 * 2 ** (job.attempts - 1)))
            logger.warning('Vote verification job %d attempt %d: %s (%s)',
                job.pk, job.attempts, job.state, job.last_error_code)
        else:
            job.state = 'complete'
            job.completed_at = datetime.datetime.utcnow()
            job.last_error_code = ''
        job.save(update_fields=['attempts', 'state', 'next_attempt_at',
                                'completed_at', 'last_error_code'])
    return True
