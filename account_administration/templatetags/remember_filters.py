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
