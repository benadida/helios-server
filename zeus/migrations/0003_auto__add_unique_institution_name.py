# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'Institution', fields ['name']
        db.create_unique('zeus_institution', ['name'])


    def backwards(self, orm):
        # Removing unique constraint on 'Institution', fields ['name']
        db.delete_unique('zeus_institution', ['name'])


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
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'zeus.secretauthcode': {
            'Meta': {'unique_together': "(('election_uuid', 'voter_login'),)", 'object_name': 'SecretAuthcode'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '63', 'primary_key': 'True'}),
            'election_uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voter_login': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['zeus']