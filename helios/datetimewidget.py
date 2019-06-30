# -*- coding: utf-8 -*-
# utils/widgets.py

'''
DateTimeWidget using JSCal2 from http://www.dynarch.com/projects/calendar/

django snippets 1629
'''

from django.utils.encoding import force_unicode
from django.conf import settings
from django import forms
import datetime, time
from django.utils.safestring import mark_safe

# DATETIMEWIDGET
calbtn = '''<img src="%smedia/admin/img/admin/icon_calendar.gif" alt="calendar" id="%s_btn" style="cursor: pointer;" title="Select date" />
<script type="text/javascript">
    Calendar.setup({
        inputField     :    "%s",
        dateFormat     :    "%s",
        trigger        :    "%s_btn",
        showTime: true
    });
</script>'''

class DateTimeWidget(forms.widgets.TextInput):
    template_name = ''

    class Media:
        css = {
            'all': (
                    '/static/helios/jscal/css/jscal2.css',
                    '/static/helios/jscal/css/border-radius.css',
                    '/static/helios/jscal/css/win2k/win2k.css',
                    )
        }
        js = (
              '/static/helios/jscal/js/jscal2.js',
              '/static/helios/jscal/js/lang/en.js',
        )

    dformat = '%Y-%m-%d %H:%M'
    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            try:
                final_attrs['value'] = \
                                   force_unicode(value.strftime(self.dformat))
            except:
                final_attrs['value'] = \
                                   force_unicode(value)
        if 'id' not in final_attrs:
            final_attrs['id'] = '%s_id' % (name)
        id = final_attrs['id']

        jsdformat = self.dformat #.replace('%', '%%')
        cal = calbtn % (settings.MEDIA_URL, id, id, jsdformat, id)
        a = '<input%s />%s%s' % (forms.util.flatatt(final_attrs), self.media, cal)
        return mark_safe(a)

    def value_from_datadict(self, data, files, name):
        dtf = forms.fields.DEFAULT_DATETIME_INPUT_FORMATS
        empty_values = forms.fields.EMPTY_VALUES

        value = data.get(name, None)
        if value in empty_values:
            return None
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)
        for format in dtf:
            try:
                return datetime.datetime(*time.strptime(value, format)[:6])
            except ValueError:
                continue
        return None

    def _has_changed(self, initial, data):
        """
        Return True if data differs from initial.
        Copy of parent's method, but modify value with strftime function before final comparsion
        """
        if data is None:
            data_value = ''
        else:
            data_value = data

        if initial is None:
            initial_value = ''
        else:
            initial_value = initial

        try:
            if force_unicode(initial_value.strftime(self.dformat)) != force_unicode(data_value.strftime(self.dformat)):
                return True
        except:
            if force_unicode(initial_value) != force_unicode(data_value):
                return True

        return False
