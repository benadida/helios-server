# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Election'
        db.create_table('helios_election', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('admin', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios_auth.User'])),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('public_key', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('private_key', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('questions', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('eligibility', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('openreg', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('featured_p', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('use_voter_aliases', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('cast_url', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('frozen_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('archived_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('registration_starts_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voting_starts_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voting_ends_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('tallying_starts_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voting_started_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voting_extended_until', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voting_ended_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('tallying_started_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('tallying_finished_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('tallies_combined_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voters_hash', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
            ('encrypted_tally', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('result', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('result_proof', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
        ))
        db.send_create_signal('helios', ['Election'])

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
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Election'])),
            ('voter_file', self.gf('django.db.models.fields.files.FileField')(max_length=250)),
            ('uploaded_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('processing_started_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('processing_finished_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('num_voters', self.gf('django.db.models.fields.IntegerField')(null=True)),
        ))
        db.send_create_signal('helios', ['VoterFile'])

        # Adding model 'Voter'
        db.create_table('helios_voter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Election'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200, null=True)),
            ('voter_type', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('voter_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('alias', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
            ('vote', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('vote_hash', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
            ('cast_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal('helios', ['Voter'])

        # Adding model 'CastVote'
        db.create_table('helios_castvote', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('voter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Voter'])),
            ('vote', self.gf('helios_auth.jsonfield.JSONField')()),
            ('vote_hash', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('cast_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('verified_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('invalidated_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal('helios', ['CastVote'])

        # Adding model 'AuditedBallot'
        db.create_table('helios_auditedballot', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Election'])),
            ('raw_vote', self.gf('django.db.models.fields.TextField')()),
            ('vote_hash', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('added_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('helios', ['AuditedBallot'])

        # Adding model 'Trustee'
        db.create_table('helios_trustee', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Election'])),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('secret', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('public_key', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('public_key_hash', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('secret_key', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('pok', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('decryption_factors', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('decryption_proofs', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
        ))
        db.send_create_signal('helios', ['Trustee'])


    def backwards(self, orm):
        
        # Deleting model 'Election'
        db.delete_table('helios_election')

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

        # Deleting model 'Trustee'
        db.delete_table('helios_trustee')


    models = {
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.auditedballot': {
            'Meta': {'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.castvote': {
            'Meta': {'object_name': 'CastVote'},
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios_auth.jsonfield.JSONField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'eligibility': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'encrypted_tally': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'questions': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'result_proof': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.trustee': {
            'Meta': {'object_name': 'Trustee'},
            'decryption_factors': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'decryption_proofs': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'voter_type': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['helios']
