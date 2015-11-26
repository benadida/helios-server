from django import template

register = template.Library()


@register.simple_tag
def active(request, location):
    if location in request.path:
        return 'active'
    return ''
