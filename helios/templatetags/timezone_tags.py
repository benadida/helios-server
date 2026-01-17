"""
Template tags for timezone display in Helios
"""

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
import datetime

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

  # Only accept datetime objects to prevent XSS
  # Note: datetime.datetime is a subclass of datetime.date, so check datetime first
  if isinstance(value, datetime.datetime):
    # Format datetime with time
    formatted = value.strftime('%Y-%m-%d %H:%M')
  elif isinstance(value, datetime.date):
    # Format date only (no time component)
    formatted = value.strftime('%Y-%m-%d 00:00')
  else:
    # Reject any other type and escape it
    return escape(str(value))

  # Escape the formatted string to prevent XSS
  escaped_formatted = escape(formatted)

  # Return HTML with data attribute for JavaScript processing
  return mark_safe(f'<span class="tz-timestamp" data-utc-time="{escaped_formatted}">{escaped_formatted} UTC</span>')
