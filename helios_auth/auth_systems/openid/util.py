
"""
Utility code for the Django example consumer and server.
"""

from urllib.parse import urljoin

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.urls import reverse as reverseURL
from openid.store import sqlstore
from openid.store.filestore import FileOpenIDStore


def getOpenIDStore(filestore_path, table_prefix):
    """
    Returns an OpenID association store object based on the database
    engine chosen for this Django application.

    * If no database engine is chosen, a filesystem-based store will
      be used whose path is filestore_path.

    * If a database engine is chosen, a store object for that database
      type will be returned.

    * If the chosen engine is not supported by the OpenID library,
      raise ImproperlyConfigured.

    * If a database store is used, this will create the tables
      necessary to use it.  The table names will be prefixed with
      table_prefix.  DO NOT use the same table prefix for both an
      OpenID consumer and an OpenID server in the same database.

    The result of this function should be passed to the Consumer
    constructor as the store parameter.
    """

    db_engine = settings.DATABASES['default']['ENGINE']
    if not db_engine:
        return FileOpenIDStore(filestore_path)

    # get the suffix
    db_engine = db_engine.split('.')[-1]

    # Possible side-effect: create a database connection if one isn't
    # already open.
    connection.cursor()

    # Create table names to specify for SQL-backed stores.
    tablenames = {
        'associations_table': table_prefix + 'openid_associations',
        'nonces_table': table_prefix + 'openid_nonces',
        }

    types = {
        'postgresql': sqlstore.PostgreSQLStore,
        'postgresql_psycopg2': sqlstore.PostgreSQLStore,
        'mysql': sqlstore.MySQLStore,
        'sqlite3': sqlstore.SQLiteStore,
        }

    try:
        s = types[db_engine](connection.connection,
                                            **tablenames)
    except KeyError:
        raise ImproperlyConfigured("Database engine %s not supported by OpenID library" % \
              (db_engine,))

    try:
        s.createTables()
    except (SystemExit, KeyboardInterrupt, MemoryError) as e:
        raise e
    except:
        # XXX This is not the Right Way to do this, but because the
        # underlying database implementation might differ in behavior
        # at this point, we can't reliably catch the right
        # exception(s) here.  Ideally, the SQL store in the OpenID
        # library would catch exceptions that it expects and fail
        # silently, but that could be bad, too.  More ideally, the SQL
        # store would not attempt to create tables it knows already
        # exists.
        pass

    return s

def getViewURL(req, view_name_or_obj, args=None, kwargs=None):
    relative_url = reverseURL(view_name_or_obj, args=args, kwargs=kwargs)
    full_path = req.META.get('SCRIPT_NAME', '') + relative_url
    return urljoin(getBaseURL(req), full_path)

def getBaseURL(req):
    """
    Given a Django web request object, returns the OpenID 'trust root'
    for that request; namely, the absolute URL to the site root which
    is serving the Django request.  The trust root will include the
    proper scheme and authority.  It will lack a port if the port is
    standard (80, 443).
    """
    name = req.META['HTTP_HOST']
    try:
        name = name[:name.index(':')]
    except:
        pass

    try:
        port = int(req.META['SERVER_PORT'])
    except:
        port = 80

    proto = req.META['SERVER_PROTOCOL']

    if 'HTTPS' in proto:
        proto = 'https'
    else:
        proto = 'http'

    if port in [80, 443] or not port:
        port = ''
    else:
        port = ':%s' % (port,)

    url = "%s://%s%s/" % (proto, name, port)
    return url

def normalDict(request_data):
    """
    Converts a django request MutliValueDict (e.g., request.GET,
    request.POST) into a standard python dict whose values are the
    first value from each of the MultiValueDict's value lists.  This
    avoids the OpenID library's refusal to deal with dicts whose
    values are lists, because in OpenID, each key in the query arg set
    can have at most one value.
    """
    return dict((k, v[0]) for k, v in request_data.items())

