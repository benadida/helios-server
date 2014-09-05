import re

from django import template
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

register = template.Library()

@register.simple_tag
def active(request, location):
    if location in request.path:
        return 'active'
    return ''
