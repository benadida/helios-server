from django.conf.urls.defaults import *
from django.core.urlresolvers import reverse


def set_menu(menu, ctx):
    ctx['menu_active'] = menu

def common_json_handler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    return unicode(obj)
