# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'MixedAnswers'
        db.create_table('helios_mixedanswers', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mixnet', self.gf('django.db.models.fields.related.ForeignKey')(related_name='mixed_answers', to=orm['helios.ElectionMixnet'])),
            ('question', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('mixed_answers', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True)),
            ('shuffling_proof', self.gf('django.db.models.fields.TextField')(null=True)),
        ))
        db.send_create_signal('helios', ['MixedAnswers'])

        # Adding unique constraint on 'MixedAnswers', fields ['mixnet', 'question']
        db.create_unique('helios_mixedanswers', ['mixnet_id', 'question'])

        # Adding model 'ElectionMixnet'
        db.create_table('helios_electionmixnet', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(default='Helios mixnet', max_length=255)),
            ('mixnet_type', self.gf('django.db.models.fields.CharField')(default='local', max_length=255)),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(related_name='mixnets', to=orm['helios.Election'])),
            ('mix_order', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('remote_ip', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('remote_protocol', self.gf('django.db.models.fields.CharField')(default='helios', max_length=255)),
            ('mixing_started_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('mixing_finished_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=255)),
            ('mix_error', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('helios', ['ElectionMixnet'])

        # Adding unique constraint on 'ElectionMixnet', fields ['election', 'mix_order']
        db.create_unique('helios_electionmixnet', ['election_id', 'mix_order'])

        # Adding unique constraint on 'ElectionMixnet', fields ['election', 'name']
        db.create_unique('helios_electionmixnet', ['election_id', 'name'])

        # Adding field 'Election.workflow_type'
        db.add_column('helios_election', 'workflow_type',
                      self.gf('django.db.models.fields.CharField')(default='homomorphic', max_length=250),
                      keep_default=False)


    def backwards(self, orm):
        # Removing unique constraint on 'ElectionMixnet', fields ['election', 'name']
        db.delete_unique('helios_electionmixnet', ['election_id', 'name'])

        # Removing unique constraint on 'ElectionMixnet', fields ['election', 'mix_order']
        db.delete_unique('helios_electionmixnet', ['election_id', 'mix_order'])

        # Removing unique constraint on 'MixedAnswers', fields ['mixnet', 'question']
        db.delete_unique('helios_mixedanswers', ['mixnet_id', 'question'])

        # Deleting model 'MixedAnswers'
        db.delete_table('helios_mixedanswers')

        # Deleting model 'ElectionMixnet'
        db.delete_table('helios_electionmixnet')

        # Deleting field 'Election.workflow_type'
        db.delete_column('helios_election', 'workflow_type')


    models = {
        'auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('auth.jsonfield.JSONField', [], {'null': 'True'}),
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
            'quarantined_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'released_from_quarantine_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'complaint_period_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'legacy/Election'", 'max_length': '250'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'election'", 'max_length': '250'}),
            'eligibility': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'encrypted_tally': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'private_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'questions': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'result_proof': ('auth.jsonfield.JSONField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_advanced_audit_features': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'workflow_type': ('django.db.models.fields.CharField', [], {'default': "'homomorphic'", 'max_length': '250'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.electionmixnet': {
            'Meta': {'ordering': "['-mix_order']", 'unique_together': "[('election', 'mix_order'), ('election', 'name')]", 'object_name': 'ElectionMixnet'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'mixnets'", 'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mix_error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'mix_order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'mixing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'mixing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'mixnet_type': ('django.db.models.fields.CharField', [], {'default': "'local'", 'max_length': '255'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'Helios mixnet'", 'max_length': '255'}),
            'remote_ip': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'remote_protocol': ('django.db.models.fields.CharField', [], {'default': "'helios'", 'max_length': '255'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '255'})
        },
        'helios.mixedanswers': {
            'Meta': {'unique_together': "(('mixnet', 'question'),)", 'object_name': 'MixedAnswers'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mixed_answers': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'mixnet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'mixed_answers'", 'to': "orm['helios.ElectionMixnet']"}),
            'question': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'shuffling_proof': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        'helios.trustee': {
            'Meta': {'object_name': 'Trustee'},
            'decryption_factors': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'decryption_proofs': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'unique_together': "(('election', 'voter_login_id'),)", 'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_login_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'voter_password': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250', 'null': 'True'}),
            'voter_file_content': ('django.db.models.fields.TextField', [], {'null': 'True'})
        }
    }

    complete_apps = ['helios']