import json
from dateutil.tz import tzutc

UTC = tzutc()

# from http://stackoverflow.com/questions/12289466/get-python-json-to-serialize-datetime
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
