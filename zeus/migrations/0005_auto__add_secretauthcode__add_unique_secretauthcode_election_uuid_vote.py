# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'SecretAuthcode'
        db.create_table('zeus_secretauthcode', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=63, primary_key=True)),
            ('election_uuid', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('voter_login', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('zeus', ['SecretAuthcode'])

        # Adding unique constraint on 'SecretAuthcode', fields ['election_uuid', 'voter_login']
        db.create_unique('zeus_secretauthcode', ['election_uuid', 'voter_login'])


    def backwards(self, orm):
        # Removing unique constraint on 'SecretAuthcode', fields ['election_uuid', 'voter_login']
        db.delete_unique('zeus_secretauthcode', ['election_uuid', 'voter_login'])

        # Deleting model 'SecretAuthcode'
        db.delete_table('zeus_secretauthcode')


    models = {
        'zeus.electioninfo': {
            'Meta': {'object_name': 'ElectionInfo'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stage': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zeus.institution': {
            'Meta': {'object_name': 'Institution'},
            'ecounting_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
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