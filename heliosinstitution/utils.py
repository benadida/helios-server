import json
from dateutil.tz import tzutc

UTC = tzutc()

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
def serialize_date(dt):
    """
    Serialize a date/time value into an ISO8601 text representation
    adjusted (if needed) to UTC timezone.

    For instance:
    >>> serialize_date(datetime(2012, 4, 10, 22, 38, 20, 604391))
    '2012-04-10T22:38:20.604391Z'
    """
    if dt is not None and dt.tzinfo:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
        return dt.isoformat() + 'Z'
    
    return ""
