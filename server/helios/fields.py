from time import strptime, strftime
import datetime
from django import forms
from django.db import models
from django.forms import fields
from .widgets import SplitSelectDateTimeWidget

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

