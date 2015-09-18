import pytz


from django.conf import settings
from django.utils import timezone


def elections_as_json(elections):
    elections_as_json = []
    for election in elections:
        election_dict = {
             'pk': election.pk,
             'uuid': election.uuid,
             'name': election.name,
             'url': election.url,
             'admin': election.admin.pretty_name,
             'voters': election.num_voters,
             'cast_votes': election.num_cast_votes,
             'started_at': serialize_date(election.frozen_at, True),
             'ended_at': serialize_date(election.voting_ended_at, True),
        }           
        elections_as_json.append(election_dict)

    return elections_as_json


def serialize_date(dt,utc=False):
    """
    Given a datetime make it timezone aware or not and format it for returning
    in a json response. Most of dates in helios are saved as datetime.datetime.utcnow()
    but some as created_at are not.
    If you configure USE_TZ as true in settings.py, you'll have one more utc offset,
    so now we don't use this setting and manually make dt timezone aware.
    """
    fmt = "%Y-%m-%d %H:%M:%S"

    if settings.TIME_ZONE == 'America/Sao_Paulo':
        fmt = "%d/%m/%Y %H:%M:%S"

    if dt is not None:
        if utc:
            est = pytz.timezone(settings.TIME_ZONE)
            dt = timezone.make_aware(dt, pytz.UTC)
            return dt.astimezone(est).strftime(fmt)
        else:
            return dt.strftime(fmt)
    
    return ""
    