# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Institution.is_disabled'
        db.add_column('zeus_institution', 'is_disabled',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Institution.is_disabled'
        db.delete_column('zeus_institution', 'is_disabled')


    models = {
        'zeus.electioninfo': {
            'Meta': {'object_name': 'ElectionInfo'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zeus.institution': {
            'Meta': {'object_name': 'Institution'},
            'ecounting_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'zeus.secretauthcode': {
            'Meta': {'unique_together': "(('election_uuid', 'voter_login'),)", 'object_name': 'SecretAuthcode'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '63', 'primary_key': 'True'}),
            'election_uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voter_login': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['zeus']