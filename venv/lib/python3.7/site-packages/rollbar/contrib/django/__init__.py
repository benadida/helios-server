from django.db.models import query
from rollbar import blacklisted_local_types

# QuerySet objects will potentially execute SQL if you call repr() on them
blacklisted_local_types.extend([query.QuerySet])
