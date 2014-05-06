from django import template
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
register = template.Library()


@register.simple_tag
def get_filters_for_url(get):
    filters_for_url = ""
    if 'inst_filter' in get:
        if get['inst_filter']:
            filters_for_url += "&inst_filter="+get['inst_filter']
    if 'uname_filter' in get:
        if get['uname_filter']:
            filters_for_url += "&uname_filter="+get['uname_filter']
    return filters_for_url

@register.simple_tag
def show_active_filters(get):
    active_filters = ""
    if 'inst_filter' in get:
        if get['inst_filter']:
            active_filters = _("Active filters => ")
    if 'uname_filter' in get:
        if get['uname_filter']:
            active_filters = _("Active filters => ")
    if 'inst_filter' in get:
        if get['inst_filter']:
            active_filters += _("Institution: ")+get['inst_filter']
    if 'uname_filter' in get:
        if get['uname_filter']:
            active_filters += " User ID: "+get['uname_filter']
    return active_filters+"</br>"

@register.simple_tag
def read_dict(the_dict, the_key):
    return the_dict[the_key]

@register.simple_tag
def clear_filters_for_user(get):
    if 'inst_filter' in get or 'uname_filter' in get:
        if get.get('inst_filter') or get.get('uname_filter'):
            clear = _("Clear Filters")
            url = reverse('list_users')
            return ("<a href="+url+">"+clear+"</a></br>")
    else:
        return "</br>"

@register.simple_tag
def clear_filters_for_institution(get):
    if 'inst_filter' in get:
        if get['inst_filter']:
            clear = _("Clear Filters")
            url = reverse('list_institutions')
            return ("<a href="+url+">"+
                    clear+"</a></br>")
    else:
        return '</br>' 
