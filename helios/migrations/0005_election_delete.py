# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('helios', '0004_auto_20170528_2025'),
    ]

    operations = [
        migrations.AddField(
            model_name='election',
            name='deleted_at',
            field=models.DateTimeField(default=None, null=True),
            preserve_default=True,
        ),
    ]
