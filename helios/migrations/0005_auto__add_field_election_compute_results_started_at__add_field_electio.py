# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Election.compute_results_started_at'
        db.add_column('helios_election', 'compute_results_started_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=None, null=True),
                      keep_default=False)

        # Adding field 'Election.compute_results_finished_at'
        db.add_column('helios_election', 'compute_results_finished_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=None, null=True),
                      keep_default=False)

        # Adding field 'Election.compute_results_status'
        db.add_column('helios_election', 'compute_results_status',
                      self.gf('django.db.models.fields.CharField')(default='pending', max_length=50),
                      keep_default=False)

        # Adding field 'Election.compute_results_error'
        db.add_column('helios_election', 'compute_results_error',
                      self.gf('django.db.models.fields.TextField')(default=None, null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Election.compute_results_started_at'
        db.delete_column('helios_election', 'compute_results_started_at')

        # Deleting field 'Election.compute_results_finished_at'
        db.delete_column('helios_election', 'compute_results_finished_at')

        # Deleting field 'Election.compute_results_status'
        db.delete_column('helios_election', 'compute_results_status')

        # Deleting field 'Election.compute_results_error'
        db.delete_column('helios_election', 'compute_results_error')


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
            'compute_results_error': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'compute_results_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'compute_results_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'compute_results_status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '50'}),
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
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 9, 20, 0, 0)', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 9, 19, 0, 0)', 'null': 'True'})
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
            'Meta': {'unique_together': "(('poll', 'voter_login_id'), ('poll', 'voter_password'))", 'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'audit_passwords': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'exclude_reason': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'excluded_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_booth_invitation_send_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'last_email_send_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'last_sms_send_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
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
            'voter_mobile': ('django.db.models.fields.CharField', [], {'max_length': '48', 'null': 'True'}),
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