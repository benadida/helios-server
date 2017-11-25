# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import helios_auth.jsonfield


class Migration(migrations.Migration):

    dependencies = [
        ('helios_auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HeliosLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('model', models.CharField(max_length=200, null=True)),
                ('description', helios_auth.jsonfield.JSONField()),
                ('at', models.DateTimeField(auto_now_add=True)),
                ('ip', models.IPAddressField(null=True)),
                ('action_type', models.CharField(default=b'MODIFY', max_length=250, choices=[(b'ADD', 'Add'), (b'DEL', 'Delete'), (b'MODIFY', 'Modify')])),
                ('user', models.ForeignKey(to='helios_auth.User')),
            ],
        ),
    ]
