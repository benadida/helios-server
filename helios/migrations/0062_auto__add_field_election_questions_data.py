# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Election.questions_data'
        db.add_column('helios_election', 'questions_data',
                      self.gf('heliosauth.jsonfield.JSONField')(null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Election.questions_data'
        db.delete_column('helios_election', 'questions_data')


    models = {
        'helios.auditedballot': {
            'Meta': {'unique_together': "(('election', 'is_request', 'fingerprint'),)", 'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'audit_code': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_request': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'signature': ('heliosauth.jsonfield.JSONField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']", 'null': 'True'})
        },
        'helios.castvote': {
            'Meta': {'unique_together': "(('election', 'index'),)", 'object_name': 'CastVote'},
            'audit_code': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'previous': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'quarantined_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'released_from_quarantine_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'signature': ('heliosauth.jsonfield.JSONField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'elections'", 'symmetrical': 'False', 'to': "orm['heliosauth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cancel_msg': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'canceled_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'candidates': ('heliosauth.jsonfield.JSONField', [], {'default': "'{}'"}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'complaint_period_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'legacy/Election'", 'max_length': '250'}),
            'departments': ('heliosauth.jsonfield.JSONField', [], {'default': "'[]'"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'ecounting_request_error': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'ecounting_request_send': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'ecounting'", 'max_length': '250'}),
            'eligibility': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'eligibles_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'encrypted_tally': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'has_department_limit': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'help_email': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'}),
            'help_phone': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zeus.Institution']", 'null': 'True'}),
            'is_completed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'mix_key': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'mixing_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'private_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'questions': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'questions_data': ('heliosauth.jsonfield.JSONField', [], {'null': 'True'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'remote_mixnets_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'result_proof': ('heliosauth.jsonfield.JSONField', [], {'null': 'True'}),
            'send_email_on_cast_done': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
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
            'workflow_type': ('django.db.models.fields.CharField', [], {'default': "'homomorphic'", 'max_length': '250'}),
            'zeus_fingerprint': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.electionmixnet': {
            'Meta': {'ordering': "['-mix_order']", 'unique_together': "[('election', 'mix_order')]", 'object_name': 'ElectionMixnet'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'mixnets'", 'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mix': ('heliosauth.jsonfield.JSONField', [], {'null': 'True'}),
            'mix_error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'mix_file': ('django.db.models.fields.files.FileField', [], {'default': 'None', 'max_length': '100', 'null': 'True'}),
            'mix_order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'mixing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'mixing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'mixnet_type': ('django.db.models.fields.CharField', [], {'default': "'local'", 'max_length': '255'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'Helios mixnet'", 'max_length': '255'}),
            'remote_ip': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'remote_protocol': ('django.db.models.fields.CharField', [], {'default': "'zeus_client'", 'max_length': '255'}),
            'second_mix': ('heliosauth.jsonfield.JSONField', [], {'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '255'})
        },
        'helios.mixparts': {
            'Meta': {'object_name': 'MixParts'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mix': ('helios.byte_fields.ByteaField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'mixnet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parts'", 'to': "orm['helios.ElectionMixnet']"})
        },
        'helios.trustee': {
            'Meta': {'object_name': 'Trustee'},
            'decryption_factors': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'decryption_proofs': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_verified_key_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
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
            'audit_passwords': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'exclude_reason': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'excluded_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_email_send_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'last_visit': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['heliosauth.User']", 'null': 'True'}),
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
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
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