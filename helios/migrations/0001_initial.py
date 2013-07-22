# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'PollMix'
        db.create_table('helios_pollmix', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(default='Zeus mixnet', max_length=255)),
            ('mix_type', self.gf('django.db.models.fields.CharField')(default='local', max_length=255)),
            ('poll', self.gf('django.db.models.fields.related.ForeignKey')(related_name='mixes', to=orm['helios.Poll'])),
            ('mix_order', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('remote_ip', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('remote_protocol', self.gf('django.db.models.fields.CharField')(default='zeus_client', max_length=255)),
            ('mixing_started_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('mixing_finished_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=255)),
            ('mix_error', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('mix_file', self.gf('django.db.models.fields.files.FileField')(default=None, max_length=100, null=True)),
        ))
        db.send_create_signal('helios', ['PollMix'])

        # Adding unique constraint on 'PollMix', fields ['poll', 'mix_order']
        db.create_unique('helios_pollmix', ['poll_id', 'mix_order'])

        # Adding model 'MixPart'
        db.create_table('helios_mixpart', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mix', self.gf('django.db.models.fields.related.ForeignKey')(related_name='parts', to=orm['helios.PollMix'])),
            ('data', self.gf('helios.byte_fields.ByteaField')(default=None, null=True, blank=True)),
        ))
        db.send_create_signal('helios', ['MixPart'])

        # Adding model 'Election'
        db.create_table('helios_election', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('election_module', self.gf('django.db.models.fields.CharField')(default='simple', max_length=250)),
            ('version', self.gf('django.db.models.fields.CharField')(default=1, max_length=255)),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('help_email', self.gf('django.db.models.fields.CharField')(max_length=254, null=True, blank=True)),
            ('help_phone', self.gf('django.db.models.fields.CharField')(max_length=254, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('trial', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('public_key', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True)),
            ('private_key', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True)),
            ('institution', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zeus.Institution'], null=True)),
            ('mix_key', self.gf('django.db.models.fields.CharField')(default=None, max_length=50, null=True)),
            ('remote_mixing_finished_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('canceled_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('cancelation_reason', self.gf('django.db.models.fields.TextField')(default='')),
            ('completed_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('deleted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('frozen_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voting_starts_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 9, 6, 0, 0), null=True)),
            ('voting_ends_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 9, 7, 0, 0), null=True)),
            ('voting_extended_until', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True, blank=True)),
            ('voting_ended_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('archived_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
        ))
        db.send_create_signal('helios', ['Election'])

        # Adding M2M table for field admins on 'Election'
        db.create_table('helios_election_admins', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('election', models.ForeignKey(orm['helios.election'], null=False)),
            ('user', models.ForeignKey(orm['heliosauth.user'], null=False))
        ))
        db.create_unique('helios_election_admins', ['election_id', 'user_id'])

        # Adding model 'Poll'
        db.create_table('helios_poll', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('validate_voting_started_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('validate_voting_finished_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('validate_voting_status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=50)),
            ('validate_voting_error', self.gf('django.db.models.fields.TextField')(default=None, null=True)),
            ('compute_results_started_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('compute_results_finished_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('compute_results_status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=50)),
            ('compute_results_error', self.gf('django.db.models.fields.TextField')(default=None, null=True)),
            ('partial_decrypt_started_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('partial_decrypt_finished_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('partial_decrypt_status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=50)),
            ('partial_decrypt_error', self.gf('django.db.models.fields.TextField')(default=None, null=True)),
            ('decrypt_started_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('decrypt_finished_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('decrypt_status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=50)),
            ('decrypt_error', self.gf('django.db.models.fields.TextField')(default=None, null=True)),
            ('zeus_partial_decrypt_started_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('zeus_partial_decrypt_finished_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('zeus_partial_decrypt_status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=50)),
            ('zeus_partial_decrypt_error', self.gf('django.db.models.fields.TextField')(default=None, null=True)),
            ('validate_mixing_started_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('validate_mixing_finished_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('validate_mixing_status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=50)),
            ('validate_mixing_error', self.gf('django.db.models.fields.TextField')(default=None, null=True)),
            ('mix_started_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('mix_finished_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('mix_status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=50)),
            ('mix_error', self.gf('django.db.models.fields.TextField')(default=None, null=True)),
            ('validate_create_started_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('validate_create_finished_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('validate_create_status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=50)),
            ('validate_create_error', self.gf('django.db.models.fields.TextField')(default=None, null=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(related_name='polls', to=orm['helios.Election'])),
            ('uuid', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50, db_index=True)),
            ('zeus_fingerprint', self.gf('django.db.models.fields.TextField')(default=None, null=True)),
            ('frozen_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('questions', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True)),
            ('questions_data', self.gf('heliosauth.jsonfield.JSONField')(null=True)),
            ('encrypted_tally', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True)),
            ('result', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True)),
            ('voters_last_notified_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
        ))
        db.send_create_signal('helios', ['Poll'])

        # Adding model 'ElectionLog'
        db.create_table('helios_electionlog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Election'])),
            ('log', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('helios', ['ElectionLog'])

        # Adding model 'VoterFile'
        db.create_table('helios_voterfile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('poll', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Poll'])),
            ('voter_file', self.gf('django.db.models.fields.files.FileField')(max_length=250, null=True)),
            ('voter_file_content', self.gf('django.db.models.fields.TextField')(null=True)),
            ('uploaded_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('processing_started_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('processing_finished_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('num_voters', self.gf('django.db.models.fields.IntegerField')(null=True)),
        ))
        db.send_create_signal('helios', ['VoterFile'])

        # Adding model 'Voter'
        db.create_table('helios_voter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('poll', self.gf('django.db.models.fields.related.ForeignKey')(related_name='voters', to=orm['helios.Poll'])),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('voter_login_id', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
            ('voter_password', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
            ('voter_name', self.gf('django.db.models.fields.CharField')(max_length=200, null=True)),
            ('voter_surname', self.gf('django.db.models.fields.CharField')(max_length=200, null=True)),
            ('voter_email', self.gf('django.db.models.fields.CharField')(max_length=250, null=True)),
            ('voter_fathername', self.gf('django.db.models.fields.CharField')(max_length=250, null=True)),
            ('alias', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
            ('vote', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True)),
            ('vote_hash', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
            ('vote_fingerprint', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('vote_signature', self.gf('django.db.models.fields.TextField')()),
            ('vote_index', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('cast_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('audit_passwords', self.gf('django.db.models.fields.CharField')(max_length=200, null=True)),
            ('last_email_send_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('last_booth_invitation_send_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('last_visit', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('excluded_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('exclude_reason', self.gf('django.db.models.fields.TextField')(default='')),
        ))
        db.send_create_signal('helios', ['Voter'])

        # Adding unique constraint on 'Voter', fields ['poll', 'voter_login_id']
        db.create_unique('helios_voter', ['poll_id', 'voter_login_id'])

        # Adding model 'CastVote'
        db.create_table('helios_castvote', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('voter', self.gf('django.db.models.fields.related.ForeignKey')(related_name='cast_votes', to=orm['helios.Voter'])),
            ('poll', self.gf('django.db.models.fields.related.ForeignKey')(related_name='cast_votes', to=orm['helios.Poll'])),
            ('previous', self.gf('django.db.models.fields.CharField')(default='', max_length=255)),
            ('vote', self.gf('helios.datatypes.djangofield.LDObjectField')()),
            ('vote_hash', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('vote_tinyhash', self.gf('django.db.models.fields.CharField')(max_length=50, unique=True, null=True)),
            ('cast_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('audit_code', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
            ('quarantined_p', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('released_from_quarantine_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('verified_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('invalidated_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('fingerprint', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('signature', self.gf('heliosauth.jsonfield.JSONField')(null=True)),
            ('index', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
        ))
        db.send_create_signal('helios', ['CastVote'])

        # Adding unique constraint on 'CastVote', fields ['poll', 'index']
        db.create_unique('helios_castvote', ['poll_id', 'index'])

        # Adding model 'AuditedBallot'
        db.create_table('helios_auditedballot', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('poll', self.gf('django.db.models.fields.related.ForeignKey')(related_name='audited_ballots', to=orm['helios.Poll'])),
            ('voter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Voter'], null=True)),
            ('raw_vote', self.gf('django.db.models.fields.TextField')()),
            ('vote_hash', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('added_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('fingerprint', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('audit_code', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('is_request', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('signature', self.gf('heliosauth.jsonfield.JSONField')(null=True)),
        ))
        db.send_create_signal('helios', ['AuditedBallot'])

        # Adding unique constraint on 'AuditedBallot', fields ['poll', 'is_request', 'fingerprint']
        db.create_unique('helios_auditedballot', ['poll_id', 'is_request', 'fingerprint'])

        # Adding model 'TrusteeDecryptionFactors'
        db.create_table('helios_trusteedecryptionfactors', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('trustee', self.gf('django.db.models.fields.related.ForeignKey')(related_name='partial_decryptions', to=orm['helios.Trustee'])),
            ('poll', self.gf('django.db.models.fields.related.ForeignKey')(related_name='partial_decryptions', to=orm['helios.Poll'])),
            ('decryption_factors', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True)),
            ('decryption_proofs', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True)),
        ))
        db.send_create_signal('helios', ['TrusteeDecryptionFactors'])

        # Adding unique constraint on 'TrusteeDecryptionFactors', fields ['trustee', 'poll']
        db.create_unique('helios_trusteedecryptionfactors', ['trustee_id', 'poll_id'])

        # Adding model 'Trustee'
        db.create_table('helios_trustee', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(related_name='trustees', to=orm['helios.Election'])),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('secret', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('public_key', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True)),
            ('public_key_hash', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('secret_key', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True)),
            ('pok', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True)),
            ('last_verified_key_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('last_notified_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
        ))
        db.send_create_signal('helios', ['Trustee'])


    def backwards(self, orm):
        # Removing unique constraint on 'TrusteeDecryptionFactors', fields ['trustee', 'poll']
        db.delete_unique('helios_trusteedecryptionfactors', ['trustee_id', 'poll_id'])

        # Removing unique constraint on 'AuditedBallot', fields ['poll', 'is_request', 'fingerprint']
        db.delete_unique('helios_auditedballot', ['poll_id', 'is_request', 'fingerprint'])

        # Removing unique constraint on 'CastVote', fields ['poll', 'index']
        db.delete_unique('helios_castvote', ['poll_id', 'index'])

        # Removing unique constraint on 'Voter', fields ['poll', 'voter_login_id']
        db.delete_unique('helios_voter', ['poll_id', 'voter_login_id'])

        # Removing unique constraint on 'PollMix', fields ['poll', 'mix_order']
        db.delete_unique('helios_pollmix', ['poll_id', 'mix_order'])

        # Deleting model 'PollMix'
        db.delete_table('helios_pollmix')

        # Deleting model 'MixPart'
        db.delete_table('helios_mixpart')

        # Deleting model 'Election'
        db.delete_table('helios_election')

        # Removing M2M table for field admins on 'Election'
        db.delete_table('helios_election_admins')

        # Deleting model 'Poll'
        db.delete_table('helios_poll')

        # Deleting model 'ElectionLog'
        db.delete_table('helios_electionlog')

        # Deleting model 'VoterFile'
        db.delete_table('helios_voterfile')

        # Deleting model 'Voter'
        db.delete_table('helios_voter')

        # Deleting model 'CastVote'
        db.delete_table('helios_castvote')

        # Deleting model 'AuditedBallot'
        db.delete_table('helios_auditedballot')

        # Deleting model 'TrusteeDecryptionFactors'
        db.delete_table('helios_trusteedecryptionfactors')

        # Deleting model 'Trustee'
        db.delete_table('helios_trustee')


    models = {
        'helios.auditedballot': {
            'Meta': {'unique_together': "(('poll', 'is_request', 'fingerprint'),)", 'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'audit_code': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_request': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'audited_ballots'", 'to': "orm['helios.Poll']"}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'signature': ('heliosauth.jsonfield.JSONField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']", 'null': 'True'})
        },
        'helios.castvote': {
            'Meta': {'ordering': "('-cast_at',)", 'unique_together': "(('poll', 'index'),)", 'object_name': 'CastVote'},
            'audit_code': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cast_votes'", 'to': "orm['helios.Poll']"}),
            'previous': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'quarantined_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'released_from_quarantine_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'signature': ('heliosauth.jsonfield.JSONField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cast_votes'", 'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Election'},
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'elections'", 'symmetrical': 'False', 'to': "orm['heliosauth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cancelation_reason': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'canceled_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'completed_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_module': ('django.db.models.fields.CharField', [], {'default': "'simple'", 'max_length': '250'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'help_email': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'}),
            'help_phone': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zeus.Institution']", 'null': 'True'}),
            'mix_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'private_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'remote_mixing_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'trial': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'version': ('django.db.models.fields.CharField', [], {'default': '1', 'max_length': '255'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 9, 7, 0, 0)', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 9, 6, 0, 0)', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.mixpart': {
            'Meta': {'object_name': 'MixPart'},
            'data': ('helios.byte_fields.ByteaField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mix': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parts'", 'to': "orm['helios.PollMix']"})
        },
        'helios.poll': {
            'Meta': {'ordering': "('created_at',)", 'object_name': 'Poll'},
            'compute_results_error': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'compute_results_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'compute_results_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'compute_results_status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'decrypt_error': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'decrypt_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'decrypt_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'decrypt_status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '50'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polls'", 'to': "orm['helios.Election']"}),
            'encrypted_tally': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mix_error': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'mix_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'mix_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'mix_status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '50'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'partial_decrypt_error': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'partial_decrypt_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'partial_decrypt_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'partial_decrypt_status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '50'}),
            'questions': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'questions_data': ('heliosauth.jsonfield.JSONField', [], {'null': 'True'}),
            'result': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'validate_create_error': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'validate_create_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'validate_create_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'validate_create_status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '50'}),
            'validate_mixing_error': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'validate_mixing_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'validate_mixing_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'validate_mixing_status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '50'}),
            'validate_voting_error': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'validate_voting_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'validate_voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'validate_voting_status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '50'}),
            'voters_last_notified_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'zeus_fingerprint': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'zeus_partial_decrypt_error': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'zeus_partial_decrypt_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'zeus_partial_decrypt_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'zeus_partial_decrypt_status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '50'})
        },
        'helios.pollmix': {
            'Meta': {'ordering': "['-mix_order']", 'unique_together': "[('poll', 'mix_order')]", 'object_name': 'PollMix'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mix_error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'mix_file': ('django.db.models.fields.files.FileField', [], {'default': 'None', 'max_length': '100', 'null': 'True'}),
            'mix_order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'mix_type': ('django.db.models.fields.CharField', [], {'default': "'local'", 'max_length': '255'}),
            'mixing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'mixing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'Zeus mixnet'", 'max_length': '255'}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'mixes'", 'to': "orm['helios.Poll']"}),
            'remote_ip': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'remote_protocol': ('django.db.models.fields.CharField', [], {'default': "'zeus_client'", 'max_length': '255'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '255'})
        },
        'helios.trustee': {
            'Meta': {'object_name': 'Trustee'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'trustees'", 'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_notified_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'last_verified_key_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.trusteedecryptionfactors': {
            'Meta': {'unique_together': "(('trustee', 'poll'),)", 'object_name': 'TrusteeDecryptionFactors'},
            'decryption_factors': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'decryption_proofs': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'partial_decryptions'", 'to': "orm['helios.Poll']"}),
            'trustee': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'partial_decryptions'", 'to': "orm['helios.Trustee']"})
        },
        'helios.voter': {
            'Meta': {'unique_together': "(('poll', 'voter_login_id'),)", 'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'audit_passwords': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'exclude_reason': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'excluded_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_booth_invitation_send_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'last_email_send_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'last_visit': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'voters'", 'to': "orm['helios.Poll']"}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'vote_fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'vote_index': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'vote_signature': ('django.db.models.fields.TextField', [], {}),
            'voter_email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_fathername': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_login_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'voter_password': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_surname': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Poll']"}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250', 'null': 'True'}),
            'voter_file_content': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        'heliosauth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ecounting_account': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('heliosauth.jsonfield.JSONField', [], {}),
            'institution': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zeus.Institution']", 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'superadmin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'token': ('heliosauth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zeus.institution': {
            'Meta': {'object_name': 'Institution'},
            'ecounting_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['helios']