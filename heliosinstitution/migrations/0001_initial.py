# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('helios_auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Institution',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=250)),
                ('short_name', models.CharField(max_length=100, blank=True)),
                ('main_phone', models.CharField(max_length=25)),
                ('sec_phone', models.CharField(max_length=25, blank=True)),
                ('address', models.TextField()),
                ('idp_address', models.URLField(unique=True)),
                ('upload_voters', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='InstitutionUserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=254)),
                ('expires_at', models.DateTimeField(default=None, null=True, blank=True)),
                ('active', models.BooleanField(default=False)),
                ('django_user', models.ForeignKey(to=settings.AUTH_USER_MODEL, unique=True)),
                ('helios_user', models.ForeignKey(default=None, blank=True, to='helios_auth.User', null=True)),
                ('institution', models.ForeignKey(to='heliosinstitution.Institution')),
            ],
            options={
                'permissions': (('delegate_institution_mngt', 'Can delegate institution management tasks'), ('revoke_institution_mngt', 'Can revoke institution management tasks'), ('delegate_election_mngt', 'Can delegate election management tasks'), ('revoke_election_mngt', 'Can revoke election management tasks')),
            },
        ),
    ]
