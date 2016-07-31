# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('helios', '0002_castvote_cast_ip'),
    ]

    operations = [
        migrations.AlterField(
            model_name='election',
            name='short_name',
            field=models.CharField(unique=True, max_length=100),
            preserve_default=True,
        ),
    ]
