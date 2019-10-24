from django.forms.widgets import Widget, Select, SelectDateWidget, MultiWidget
from django.conf import settings 
from django.utils.translation import gettext_lazy as _
from django.utils.formats import get_format
from django.utils import datetime_safe, formats
from django.forms.utils import to_current_timezone

import re
import datetime


class SelectTimeWidget(Widget):
    """
    A widget that splits time input into two <select> boxes.

    """
    none_value = ('', '---')
    hour_field = '%s_hour'
    minute_field = '%s_minute'
    meridiem_field = '%s_meridiem'
    twelve_hr = False # Default to 24hr.'

    template_name = 'widgets/select_time.html'
    input_type = 'select'
    select_widget = Select
    # time_pattern = r'(\d\d?):(\d\d)(:(\d\d))? *([aApP]\.?[mM]\.?)?$'
    time_pattern = r'(\d\d?):(\d\d?)$'
    time_re = re.compile(time_pattern)

    def __init__(self, attrs=None, empty_label=["00","00"]):
        self.attrs = attrs or {}

        # Optional string, list, or tuple to use as empty_label.
        if isinstance(empty_label, (list, tuple)):
            if not len(empty_label) == 2:
                raise ValueError('empty_label list/tuple must have 2 elements.')

            self.hour_none_value = ('', empty_label[0])
            self.minute_none_value = ('', empty_label[1])
        else:
            if empty_label is not None:
                self.none_value = ('', empty_label)

            self.hour_none_value = self.none_value
            self.minute_none_value = self.none_value

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        time_context = {}
        hour_choices = [("%d"%i, "%.2d"%i) for i in range(0, 24)]
        if not self.is_required:
            hour_choices.insert(0, self.hour_none_value)
        hour_name = self.hour_field % name
        time_context['hour'] = self.select_widget(attrs, choices=hour_choices).get_context(
            name=hour_name,
            value=context['widget']['value']['hour'],
            attrs={
                **context['widget']['attrs'],
                'id': 'id_%s' % hour_name,
                'placeholder': _('Hour') if self.is_required else False,
            },
        )
        minute_choices = [("%d"%i, "%.2d"%i) for i in range(1, 60)]  #list(self.minutes.items())
        if not self.is_required:
            minute_choices.insert(0, self.minute_none_value)
        minute_name = self.minute_field % name
        time_context['minute'] = self.select_widget(attrs, choices=minute_choices).get_context(
            name=minute_name,
            value=context['widget']['value']['minute'],
            attrs={
                **context['widget']['attrs'],
                'id': 'id_%s' % minute_name,
                'placeholder': _('Minute') if self.is_required else False,
            },
        )
        subwidgets = []
        for field in self._parse_time_fmt():
            subwidgets.append(time_context[field]['widget'])
        subwidgets.append(time_context['minute']['widget'])
        context['widget']['subwidgets'] = subwidgets
        return context

    def format_value(self, value):
        """
        Return a dict containing the hour and minute of the current value.

        """
        hour, minute = None, None
        # if isinstance(value, (datetime.date, datetime.datetime)):
        if isinstance(value, (datetime.time)):
            hour, minute = value.hour, value.minute
        elif isinstance(value, str):
            match = self.time_re.match(value)
            if match:
                # Convert any zeros in the date to empty strings to match the
                # empty option value.
                hour, minute = [int(val) or '' for val in match.groups()]
            elif settings.USE_L10N:
                input_format = get_format('TIME_INPUT_FORMATS')[2]
                try:
                    d = datetime.datetime.strptime(value, input_format)
                except ValueError:
                    pass
                else:
                    hour, minute = d.hour, d.minute
        return {'hour': hour, 'minute': minute}

    @staticmethod
    def _parse_time_fmt():
        fmt = get_format('TIME_FORMAT')
        escaped = False
        for char in fmt:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char in 'HhP':
                yield 'hour'
            elif char in 'Mm':
                yield 'minute'

    def id_for_label(self, id_):
        for first_select in self._parse_time_fmt():
            return '%s_%s' % (id_, first_select)
        return '%s_minute' % id_

    def value_from_datadict(self, data, files, name):
        h = data.get(self.hour_field % name, 0)
        m = data.get(self.minute_field % name, 0)

        if h == m == '':
            return None
        if h is not None and m is not None:
            input_format = get_format('TIME_INPUT_FORMATS')[2]
            try:
                time_value = datetime.time(int(h), int(m))   
            except ValueError:
                # Return pseudo-ISO dates with zeros for any unselected values,
                # e.g. '2017-0-23'.
                return '%s-%s' % (h or 0, m or 0)
            # time_value = datetime_safe.new_datetime(time_value)
            return time_value.strftime(input_format)
        return data.get(name)

    def value_omitted_from_data(self, data, files, name):
        return not any(
            ('{}_{}'.format(name, interval) in data)
            for interval in ('hour', 'minute')
        )


class SplitSelectDateTimeWidget(MultiWidget):
    supports_microseconds = False
    template_name = 'widgets/split_select_date_time.html'

    def __init__(self, attrs=None, date_format=None, time_format=None, date_attrs=None, time_attrs=None):
        widgets = (
            SelectDateWidget(
                attrs=attrs if date_attrs is None else date_attrs,
                # format=date_format,
            ),
            SelectTimeWidget(
                attrs=attrs if time_attrs is None else time_attrs,
                # format=time_format,
            )
        )
        super().__init__(widgets)

    def decompress(self, value):
        if value:
            value = to_current_timezone(value)
            return [value.date(), value.time()]
        return [None, None]


    def value_from_datadict(self, data, files, name):
        if data.get(name, None) is None:
            return [widget.value_from_datadict(data, files, name + '_%s' % i) for i, widget in enumerate(self.widgets)]
        return self.decompress(data.get(name, None))

