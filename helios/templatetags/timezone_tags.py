"""
Template tags for timezone display in Helios
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='utc_time')
def utc_time(value):
  """
  Marks a datetime value for automatic timezone conversion.
  The JavaScript will convert this to show both UTC and local timezone.

  Usage in templates:
    {{ election.voting_starts_at|utc_time }}
  """
  if value is None:
    return ''

  # Format the datetime for display
  if hasattr(value, 'strftime'):
    formatted = value.strftime('%Y-%m-%d %H:%M')
  else:
    formatted = str(value)

  # Return HTML with data attribute for JavaScript processing
  return mark_safe(f'<span class="tz-timestamp" data-utc-time="{formatted}">{formatted} UTC</span>')
