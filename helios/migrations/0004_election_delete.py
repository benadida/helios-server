# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('helios', '0003_auto_20160507_1948'),
    ]

    operations = [
        migrations.AddField(
            model_name='election',
            name='deleted_at',
            field=models.DateTimeField(default=None, null=True),
            preserve_default=True,
        ),
    ]
