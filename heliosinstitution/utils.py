import pytz


from django.conf import settings


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
             'started_at': serialize_date(election.frozen_at),
             'ended_at': serialize_date(election.voting_ended_at),
        }           
        elections_as_json.append(election_dict)

    return elections_as_json

    # based on http://stackoverflow.com/questions/12289466/get-python-json-to-serialize-datetime
def serialize_date(dt):
    """
    Serialize a date/time value into an ISO8601 text representation
    adjusted (if needed) to UTC timezone.

    For instance:
    >>> serialize_date(datetime(2012, 4, 10, 22, 38, 20, 604391))
    '2012-04-10T22:38:20.604391Z'
    """
    if dt is not None and dt.tzinfo:
        est = pytz.timezone(settings.TIME_ZONE)
        dt = dt.astimezone(est).replace(tzinfo=None)
        return dt.isoformat() + 'Z'
    
    return ""