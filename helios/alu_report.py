"""Aggregate election operations. Never serialize identities or ballot contents."""
import datetime
from django.db.models import Avg, Count, DateTimeField, DurationField, ExpressionWrapper, F, Q, Value
from django.db.models.functions import TruncDate
from django.utils import timezone
from helios import models


def operational_report(election, closed):
    casts = models.CastVote.objects.filter(voter__election=election)
    verified = casts.filter(Q(quarantined_p=False) | Q(released_from_quarantine_at__isnull=False),
                            verified_at__isnull=False, invalidated_at__isnull=True)
    duration = ExpressionWrapper(F('verified_at') - F('cast_at'), output_field=DurationField())
    average = verified.filter(verified_at__gte=F('cast_at')).aggregate(value=Avg(duration))['value']
    buckets = None
    series_status = 'voting_not_closed'
    if closed:
        # Helios records naive UTC datetimes (USE_TZ=False). Shift its recorded
        # UTC clock to Kigali before grouping; Django ignores tzinfo in this mode.
        # Whole series withheld if any populated day has fewer than five voters.
        # No timestamps, tracker, IP, session, ciphertext or voter ID leave here.
        rows = list(models.Voter.objects.filter(election=election, vote__isnull=False)
                    .annotate(day=TruncDate(ExpressionWrapper(F('cast_at') + Value(datetime.timedelta(hours=2)), output_field=DateTimeField())))
                    .values('day').annotate(count=Count('id')).order_by('day'))
        if any(row['day'] is None for row in rows):
            series_status = 'not_collected'
        elif any(row['count'] < 5 for row in rows):
            series_status = 'small_groups'
        elif len(rows) > 366:
            series_status = 'too_many_days'
        else:
            series_status = 'available'
            buckets = [{'day': row['day'].isoformat(), 'votes': row['count']} for row in rows]
    def iso(value):
        if value is None:
            return None
        if timezone.is_naive(value):
            value = timezone.make_aware(value, datetime.timezone.utc)
        return value.isoformat()
    return {
        'registered': election.voter_set.count(),
        'cast_records': casts.count(),
        'verified_records': verified.count(),
        'invalid_records': casts.filter(invalidated_at__isnull=False).count(),
        'quarantined_records': casts.filter(quarantined_p=True, released_from_quarantine_at__isnull=True).count(),
        'verification_seconds': round(average.total_seconds(), 2) if average is not None else None,
        'vote_days': buckets, 'vote_days_status': series_status,
        'dates': {key: iso(getattr(election, key)) for key in (
            'frozen_at', 'voting_started_at', 'voting_starts_at', 'voting_ended_at',
            'voting_ends_at', 'tallying_started_at', 'tallying_finished_at',
            'tallies_combined_at', 'result_released_at')},
    }
