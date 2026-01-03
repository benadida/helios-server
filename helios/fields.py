import datetime

from django.forms import fields

from .widgets import SplitSelectDateTimeWidget, DateTimeLocalWidget


class SplitDateTimeField(fields.MultiValueField):
    widget = SplitSelectDateTimeWidget

    def __init__(self, *args, **kwargs):
        """
        Have to pass a list of field types to the constructor, else we
        won't get any data to our compress method.
        """
        all_fields = (fields.DateField(), fields.TimeField())
        super(SplitDateTimeField, self).__init__(all_fields, *args, **kwargs)

    def compress(self, data_list):
        """
        Takes the values from the MultiWidget and passes them as a
        list to this function. This function needs to compress the
        list into a single object to save.
        """
        if data_list:
            if not (data_list[0] and data_list[1]):
                return None
            return datetime.datetime.combine(*data_list)
        return None


class DateTimeLocalField(fields.DateTimeField):
    """
    A field for HTML5 datetime-local input widget.
    Handles datetime input in the format: YYYY-MM-DDTHH:MM
    """
    widget = DateTimeLocalWidget
    input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S']

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('input_formats', self.input_formats)
        super(DateTimeLocalField, self).__init__(*args, **kwargs)

