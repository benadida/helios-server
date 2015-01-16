import os
import sys

sys.path.append('/web/helios-server')

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

if os.environ.get('ZEUS_DEV_SERVER'):
    print "ZEUS_DEV"
    import uwsgi
    from uwsgidecorators import timer
    from django.utils import autoreload

    @timer(1)
    def change_code_gracefull_reload(sig):
        if autoreload.code_changed():
            uwsgi.reload()

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
