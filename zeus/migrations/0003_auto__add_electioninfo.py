# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ElectionInfo'
        db.create_table('zeus_electioninfo', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('stage', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal('zeus', ['ElectionInfo'])


    def backwards(self, orm):
        # Deleting model 'ElectionInfo'
        db.delete_table('zeus_electioninfo')


    models = {
        'zeus.electioninfo': {
            'Meta': {'object_name': 'ElectionInfo'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stage': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'zeus.faculty': {
            'Meta': {'object_name': 'Faculty'},
            'faculty_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['zeus']