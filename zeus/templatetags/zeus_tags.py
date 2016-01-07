import json
import urllib

from functools import partial

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext as _n
from django.template.loader import render_to_string
from django.template import Template
from django.utils.html import escape

register = template.Library()


def _confirm_action(context, label, url, confirm_msg="", icon="",
                    method="POST", cls="", extra_cls="", disabled=False,
                    inline=False):

    form_cls = ""

    if not confirm_msg:
        confirm_msg = _("Are you sure ?")

    if icon == "remove" and cls == "":
        cls += " alert"

    if inline:
        form_cls += " inline"

    confirm_msg = unicode(confirm_msg)
    confirm_msg = Template(confirm_msg).render(context)
    confirm_msg = confirm_msg.replace('\n', ' ');

    confirm_code = """onsubmit="return confirm('%s');" """ % confirm_msg
    if "noconfirm" in cls:
        confirm_code = ""

    onclick = ""
    if not disabled:
        onclick = ("""onclick="$(this).closest('form').submit(); """
                   """return false" """)
    else:
        cls += " disabled"


    csrf_token = ""
    if 'csrf_token' in context:
        csrf_token = """<input type="hidden" """ + \
                     """value="%s" """ % context['csrf_token'] + \
                     """name="csrfmiddlewaretoken" />"""
    if "nocsrf" in cls:
        csrf_token = ""

    html = """
    <form action="%(url)s" method="%(method)s" class="action-form %(form_cls)s"
     %(confirm_code)s>
     %(csrf_token)s
    <a href="#" %(onclick)s
    class="button foundicon-%(icon)s %(cls)s %(extra_cls)s"> &nbsp;%(label)s</a>
    </form>
    """ % {
        'label': label,
        'url': url,
        'cls': cls,
        'extra_cls': extra_cls,
        'icon': icon,
        'method': method,
        'form_cls': form_cls,
        'confirm_code': confirm_code,
        'confirm_msg': confirm_msg,
        'csrf_token': csrf_token,
        'onclick': onclick
    }
    return html


def _action(context, label, url, icon="", cls="", extra_cls="",
            tag_content="", disabled=False):

    if disabled:
        cls += " disabled"
        if "onclick" in tag_content:
            tag_content = ""

    if not url:
        url = "#"

    if not "nobutton" in cls:
        cls += " button"

    html = """
    <a class="%(extra_cls)s %(cls)s foundicon-%(icon)s"
       href="%(url)s" %(tag_content)s> &nbsp;%(label)s</a>
    """ % {
        'label': escape(label),
        'url': url,
        'icon': icon,
        'cls': cls,
        'extra_cls': extra_cls,
        'tag_content': tag_content
    }
    return html


@register.simple_tag(takes_context=True)
def action(context, *args, **kwargs):
    return _action(context, *args, **kwargs)


@register.simple_tag(takes_context=True)
def small_action(context, *args, **kwargs):
    kwargs['extra_cls'] = 'small'
    return _action(context, *args, **kwargs)


@register.simple_tag(takes_context=True)
def medium_action(context, *args, **kwargs):
    kwargs['extra_cls'] = 'medium'
    return _action(context, *args, **kwargs)


@register.simple_tag(takes_context=True)
def confirm_action(context, *args, **kwargs):
    return _confirm_action(context, *args, **kwargs)


@register.simple_tag(takes_context=True)
def small_confirm_action(context, *args, **kwargs):
    kwargs['extra_cls'] = 'small'
    return _confirm_action(context, *args, **kwargs)


@register.simple_tag(takes_context=True)
def medium_confirm_action(context, *args, **kwargs):
    kwargs['cls'] = 'medium'
    return _confirm_action(context, *args, **kwargs)


@register.simple_tag(takes_context=True)
def menu_action(context, label, url, icon="", cls=""):
    html = """
    <li>
    <a class="foundicon-%(icon)s"
       href="%(url)s"> &nbsp;%(label)s
    </a>
    </li>
    """ % {
        'label': label,
        'url': url,
        'icon': icon
    }
    return html


@register.simple_tag(takes_context=True)
def menu_confirm_action(context, label, url, confirm_msg="", icon="",
                        method="POST", cls="", q=None):
    if not confirm_msg:
        confirm_msg = _("Are you sure ?")

    if icon == "remove" and cls == "":
        cls += " alert"

    confirm_msg = unicode(confirm_msg)
    confirm_msg = Template(confirm_msg).render(context)
    confirm_msg = confirm_msg.replace('\n', ' ')

    icon_cls = ""
    if icon:
        icon_cls = "foundicon-%s" % icon

    confirm_code = """onsubmit="return confirm('%s');" """ % confirm_msg
    if "noconfirm" in cls:
        confirm_code = ""

    csrf_token = ""
    if 'csrf_token' in context:
        csrf_token = """<input type="hidden" """ + \
                     """value="%s" """ % context['csrf_token'] + \
                     """name="csrfmiddlewaretoken" />"""
    if "nocsrf" in cls:
        csrf_token = ""
    
    q_field = "" 
    if q:
        q_field = """<input type="hidden" """ + \
                  """value="%s" """ % q + \
                  """name="q_param" \>"""

    html = """
    <li>
    <form action="%(url)s" method="%(method)s" class="action-form"
    %(confirm_code)s>
    %(csrf_token)s
    %(q_hidden_field)s
    <a href="#" onclick="$(this).closest('form').submit(); return false"
    class="%(icon)s %(cls)s"> &nbsp;%(label)s</a>
    </form>
    </li>
    """ % {
        'label': label,
        'url': url,
        'cls': cls,
        'icon': icon_cls,
        'method': method,
        'confirm_code': confirm_code,
        'confirm_msg': confirm_msg,
        'csrf_token': csrf_token,
        'q_hidden_field': q_field,
    }
    return html


@register.simple_tag(takes_context=True)
def reveal_action(context, label, selector, icon="", cls="", disabled=False):
    params = {
        'animationSpeed': 100
    }
    jsparams = json.dumps(params).replace("\"", "&quot;")
    js_content = """$('%(selector)s').reveal(%(jsparams)s);""" % {
        'selector': selector,
        'jsparams': jsparams
    }
    tag_content = """onclick="%(js_content)s return false;" """ % {
        'js_content': js_content
    }
    action_html = _action(context, label, "", icon, cls, disabled=disabled,
                          tag_content=tag_content)
    return action_html


@register.filter
def escape_plus(value):
    return value.replace("+", "%2B").replace(" ", "+")


@register.filter
def negate(value):
    return not value


@register.filter
def voters_filtered_suffix(value):
    if not value:
        value = 0
    msg = _n(
        '(1 voter selected)',
        '(%(value)d voters selected)',
        value
    ) % {'value': value}
    return msg if value else _('(all voters selected)')


@register.simple_tag(takes_context=True)
def set_election_issues(context, election):
    context['election_issues_list'] = \
        election.election_issues_before_freeze
    context['polls_issues_list'] = \
        election.polls_issues_before_freeze
    return ''

@register.simple_tag(takes_context=True)
def complete_get_parameters(context, GET, new_order,
                            default_sort_key='voter_login_id'):
    page_param = ''
    page = GET.get('page', None)
    if page:
        page_param += "&page=%s" % page
    order_by = GET.get('order', default_sort_key)
    order_type = GET.get('order_type', None)
    if order_type == None and order_by == 'created_at':
        order_type = 'desc'
    elif order_type == None:
        order_type = 'asc'
  
    order_param = ''
    if order_by == new_order:
        context['ordering_cls'] = order_type
        if order_type == 'asc':
            new_order_type = 'desc'
        else:
            new_order_type = 'asc'
    else:
        new_order_type = 'asc'
    order_param = '&order_type=%s' % new_order_type
    filter_param = ''
    q = GET.get('q', None)
    if q:
        if isinstance(q, unicode):
            q = q.encode('utf8')
        filter_param = '&q=%s' % urllib.quote_plus(q)
    params = '%s%s%s' % (page_param, order_param, filter_param)
    return params


@register.simple_tag(takes_context=True)
def fieldset_fields(context, form, fieldset, name='fieldset_'):
    context[name + 'fields'] = list(form.iter_fieldset(fieldset))
    context[name + 'helptext'] = form.fieldsets[fieldset][1]
    context[name + 'name'] = form.fieldsets[fieldset][0]
    return ''
