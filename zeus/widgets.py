# -*- coding: utf-8 -*-
from time import strptime, strftime
from django import forms
from django.db import models
from django.forms import fields
from django import forms
from django.db import models
from django.template.loader import render_to_string
from django.forms.widgets import Select, MultiWidget, DateInput, TextInput
from time import strftime


hour_selections = [(str(t), "%02d:00" % t) for t in range(24)]
class JqSplitDateTimeWidget(MultiWidget):

    def __init__(self, attrs=None, date_format=None, time_format=None):
        date_class = attrs['date_class']
        time_class = attrs['time_class']
        del attrs['date_class']
        del attrs['time_class']

        time_attrs = attrs.copy()
        time_attrs['class'] = time_class
        date_attrs = attrs.copy()
        date_attrs['class'] = date_class

        widgets = (DateInput(attrs=date_attrs, format=date_format),
                   Select(attrs=time_attrs, choices=hour_selections))

        super(JqSplitDateTimeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            d = strftime("%Y-%m-%d", value.timetuple())
            hour = strftime("%I", value.timetuple())
            print (d, hour)
            return (d, hour)
        else:
            return (None, None, None, None)

    def format_output(self, rendered_widgets):
        """
        Given a list of rendered widgets (as strings), it inserts an HTML
        linebreak between them.

        Returns a Unicode string representing the HTML for the whole lot.
        """
        return """
        <div class="row"><div class="columns ten">%s</div>
        <div class="columns two" placeholder="">%s</div>
        </div>
        """ % (rendered_widgets[0], rendered_widgets[1])


class JqSplitDateTimeField(fields.MultiValueField):
    widget = JqSplitDateTimeWidget

    def __init__(self, *args, **kwargs):
        """
        Have to pass a list of field types to the constructor, else we
        won't get any data to our compress method.
        """
        all_fields = (
            fields.CharField(max_length=10),
            fields.CharField(max_length=2),
            )
        super(JqSplitDateTimeField, self).__init__(all_fields, *args, **kwargs)

    def compress(self, data_list):
        """
        Takes the values from the MultiWidget and passes them as a
        list to this function. This function needs to compress the
        list into a single object to save.
        """
        if data_list:
            if not (data_list[0] and data_list[1]):
                raise forms.ValidationError("Field is missing data.")
            input_time = strptime("%s:00"%(data_list[1]), "%H:%M")
            datetime_string = "%s %s" % (data_list[0], strftime('%H:%M', input_time))
            return datetime_string
        return None


