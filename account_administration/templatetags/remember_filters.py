import re

from django import template
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

register = template.Library()

@register.simple_tag
def clean_query_string(request):
    get_params_string = request.META['QUERY_STRING']
    get_params = get_params_string.split('&')
    query_string = ''
    for item in get_params:
        if 'page' not in item:
            query_string += '&%s' % item
    return query_string

@register.simple_tag
def active(request, location):
    if location in request.path:
        return 'active'
    return ''

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
