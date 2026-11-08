from django import template

from helios.models import SiteAnnouncement

register = template.Library()


@register.simple_tag
def site_announcement():
  return SiteAnnouncement.current_text()
