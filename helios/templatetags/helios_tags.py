from django import template
from django.utils.translation import ugettext as _

register = template.Library()


def _d_to_dl(d):
  html = u"<dl>"
  for key in d.keys():
    html += u"<dt>%s</dt>" % _(key)
    value = d[key]
    if isinstance(value, dict):
      value = _d_to_dl(value)
    if isinstance(value, list):
      value = _l_to_table(value)

    html += u"<dd>%s</dd>" % unicode(value)

  html += u"</dl>"
  return html

def _l_to_table(l):
  if not len(l):
    return "<table></table>"

  html = u"<table>"

  if isinstance(l[0], dict):
    values = l
    html += u"<thead><tr>"
    for key in l[0].keys():
      html += u"<th>%s</th>" % _(key)
    html += "</thead></tr>"
  else:
    values = map(lambda v:{'value': v}, l)

  html += u"<tbody>"
  for entry in values:
    html += u"<tr>"
    for v in entry.values():
      html += u"<td>%s</td>" % v
    html += u"</tr>"

  html += "</tbody></table>"
  return html

@register.filter
def as_dl(d):
  return _d_to_dl(d)
as_dl.is_safe = True


@register.filter
def as_table(l):
  return _l_to_table(l)
as_dl.is_safe = True

