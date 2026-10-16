"""Aggregate election operations. Never serialize identities or ballot contents."""
import datetime
from django.db.models import Avg, Count, DateTimeField, DurationField, ExpressionWrapper, F, Q, Value
from django.db.models.functions import TruncDate
from django.utils import timezone
from helios import models


def lifecycle_dates(election, closed=None):
    """Dates and their evidence only. No tally computation or voter scan."""
    def iso(value):
        if value is None:
            return None
        if timezone.is_naive(value):
            value = timezone.make_aware(value, datetime.timezone.utc)
        return value.astimezone(datetime.timezone.utc).isoformat()
    dates = {key: iso(getattr(election, key)) for key in (
        'frozen_at', 'voting_started_at', 'voting_starts_at', 'voting_ended_at',
        'voting_ends_at', 'voting_extended_until', 'tallying_started_at',
        'tallying_finished_at', 'tallies_combined_at', 'result_released_at')}
    sources = {key: 'native_field' for key, value in dates.items() if value is not None}
    # auto_now_add log times are in Django's local timezone with USE_TZ=False,
    # unlike native election fields (naive UTC). Never rewrite historical rows.
    def from_log(key, **lookup):
        if dates[key] is not None:
            return
        at = models.ElectionLog.objects.filter(election=election, **lookup).order_by('at', 'pk').values_list('at', flat=True).first()
        if at is not None:
            if timezone.is_naive(at):
                at = timezone.make_aware(at, timezone.get_default_timezone())
            dates[key] = iso(at)
            sources[key] = 'audit_log'
    from_log('frozen_at', log=models.ElectionLog.FROZEN)
    from_log('voting_started_at', log__startswith='Voting opened manually by ')
    if election.result_released_at is not None:
        from_log('tallies_combined_at', log=models.ElectionLog.DECRYPTIONS_COMBINED)
    # A scheduled opening/closure is an effective schedule time, not an observed
    # manual action. Keep that distinction in the archived provenance.
    if dates['voting_started_at'] is None and election.frozen_at and election.voting_has_started():
        opened = max(election.frozen_at, election.voting_starts_at or election.frozen_at)
        dates['voting_started_at'] = iso(opened)
        sources['voting_started_at'] = 'effective_schedule'
    if dates['voting_ended_at'] is None and closed:
        ended = election.voting_extended_until or election.voting_ends_at
        if ended is not None and ended <= datetime.datetime.utcnow():
            dates['voting_ended_at'] = iso(ended)
            sources['voting_ended_at'] = 'effective_schedule'
    return {'dates': dates, 'date_sources': sources}


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
    lifecycle = lifecycle_dates(election, closed)
    return {
        'registered': election.voter_set.count(),
        'cast_records': casts.count(),
        'verified_records': verified.count(),
        'invalid_records': casts.filter(invalidated_at__isnull=False).count(),
        'quarantined_records': casts.filter(quarantined_p=True, released_from_quarantine_at__isnull=True).count(),
        'verification_seconds': round(average.total_seconds(), 2) if average is not None else None,
        'vote_days': buckets, 'vote_days_status': series_status,
        **lifecycle,
    }
