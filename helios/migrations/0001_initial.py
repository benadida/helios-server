# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import helios.datatypes.djangofield
import helios_auth.jsonfield
import helios.datatypes


class Migration(migrations.Migration):

    dependencies = [
        ('helios_auth', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditedBallot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('raw_vote', models.TextField()),
                ('vote_hash', models.CharField(max_length=100)),
                ('added_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CastVote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('vote', helios.datatypes.djangofield.LDObjectField()),
                ('vote_hash', models.CharField(max_length=100)),
                ('vote_tinyhash', models.CharField(max_length=50, unique=True, null=True)),
                ('cast_at', models.DateTimeField(auto_now_add=True)),
                ('quarantined_p', models.BooleanField(default=False)),
                ('released_from_quarantine_at', models.DateTimeField(null=True)),
                ('verified_at', models.DateTimeField(null=True)),
                ('invalidated_at', models.DateTimeField(null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, helios.datatypes.LDObjectContainer),
        ),
        migrations.CreateModel(
            name='Election',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.CharField(max_length=50)),
                ('datatype', models.CharField(default=b'legacy/Election', max_length=250)),
                ('short_name', models.CharField(max_length=100)),
                ('name', models.CharField(max_length=250)),
                ('election_type', models.CharField(default=b'election', max_length=250, choices=[(b'election', b'Election'), (b'referendum', b'Referendum')])),
                ('private_p', models.BooleanField(default=False)),
                ('description', models.TextField()),
                ('public_key', helios.datatypes.djangofield.LDObjectField(null=True)),
                ('private_key', helios.datatypes.djangofield.LDObjectField(null=True)),
                ('questions', helios.datatypes.djangofield.LDObjectField(null=True)),
                ('eligibility', helios.datatypes.djangofield.LDObjectField(null=True)),
                ('openreg', models.BooleanField(default=False)),
                ('featured_p', models.BooleanField(default=False)),
                ('use_voter_aliases', models.BooleanField(default=False)),
                ('use_advanced_audit_features', models.BooleanField(default=True)),
                ('randomize_answer_order', models.BooleanField(default=False)),
                ('cast_url', models.CharField(max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now_add=True)),
                ('frozen_at', models.DateTimeField(default=None, null=True)),
                ('archived_at', models.DateTimeField(default=None, null=True)),
                ('registration_starts_at', models.DateTimeField(default=None, null=True)),
                ('voting_starts_at', models.DateTimeField(default=None, null=True)),
                ('voting_ends_at', models.DateTimeField(default=None, null=True)),
                ('complaint_period_ends_at', models.DateTimeField(default=None, null=True)),
                ('tallying_starts_at', models.DateTimeField(default=None, null=True)),
                ('voting_started_at', models.DateTimeField(default=None, null=True)),
                ('voting_extended_until', models.DateTimeField(default=None, null=True)),
                ('voting_ended_at', models.DateTimeField(default=None, null=True)),
                ('tallying_started_at', models.DateTimeField(default=None, null=True)),
                ('tallying_finished_at', models.DateTimeField(default=None, null=True)),
                ('tallies_combined_at', models.DateTimeField(default=None, null=True)),
                ('result_released_at', models.DateTimeField(default=None, null=True)),
                ('voters_hash', models.CharField(max_length=100, null=True)),
                ('encrypted_tally', helios.datatypes.djangofield.LDObjectField(null=True)),
                ('result', helios.datatypes.djangofield.LDObjectField(null=True)),
                ('result_proof', helios_auth.jsonfield.JSONField(null=True)),
                ('help_email', models.EmailField(max_length=75, null=True)),
                ('election_info_url', models.CharField(max_length=300, null=True)),
                ('admin', models.ForeignKey(to='helios_auth.User')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, helios.datatypes.LDObjectContainer),
        ),
        migrations.CreateModel(
            name='ElectionLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('log', models.CharField(max_length=500)),
                ('at', models.DateTimeField(auto_now_add=True)),
                ('election', models.ForeignKey(to='helios.Election')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Trustee',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=200)),
                ('email', models.EmailField(max_length=75)),
                ('secret', models.CharField(max_length=100)),
                ('public_key', helios.datatypes.djangofield.LDObjectField(null=True)),
                ('public_key_hash', models.CharField(max_length=100)),
                ('secret_key', helios.datatypes.djangofield.LDObjectField(null=True)),
                ('pok', helios.datatypes.djangofield.LDObjectField(null=True)),
                ('decryption_factors', helios.datatypes.djangofield.LDObjectField(null=True)),
                ('decryption_proofs', helios.datatypes.djangofield.LDObjectField(null=True)),
                ('election', models.ForeignKey(to='helios.Election')),
            ],
            options={
            },
            bases=(models.Model, helios.datatypes.LDObjectContainer),
        ),
        migrations.CreateModel(
            name='Voter',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.CharField(max_length=50)),
                ('voter_login_id', models.CharField(max_length=100, null=True)),
                ('voter_password', models.CharField(max_length=100, null=True)),
                ('voter_name', models.CharField(max_length=200, null=True)),
                ('voter_email', models.CharField(max_length=250, null=True)),
                ('alias', models.CharField(max_length=100, null=True)),
                ('vote', helios.datatypes.djangofield.LDObjectField(null=True)),
                ('vote_hash', models.CharField(max_length=100, null=True)),
                ('cast_at', models.DateTimeField(null=True)),
                ('election', models.ForeignKey(to='helios.Election')),
                ('user', models.ForeignKey(to='helios_auth.User', null=True)),
            ],
            options={
            },
            bases=(models.Model, helios.datatypes.LDObjectContainer),
        ),
        migrations.CreateModel(
            name='VoterFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('voter_file', models.FileField(max_length=250, null=True, upload_to=b'voters/%Y/%m/%d')),
                ('voter_file_content', models.TextField(null=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('processing_started_at', models.DateTimeField(null=True)),
                ('processing_finished_at', models.DateTimeField(null=True)),
                ('num_voters', models.IntegerField(null=True)),
                ('election', models.ForeignKey(to='helios.Election')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='voter',
            unique_together=set([('election', 'voter_login_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='trustee',
            unique_together=set([('election', 'email')]),
        ),
        migrations.AddField(
            model_name='castvote',
            name='voter',
            field=models.ForeignKey(to='helios.Voter'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='auditedballot',
            name='election',
            field=models.ForeignKey(to='helios.Election'),
            preserve_default=True,
        ),
    ]
