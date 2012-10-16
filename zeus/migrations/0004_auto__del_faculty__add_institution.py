# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'Faculty'
        db.delete_table('zeus_faculty')

        # Adding model 'Institution'
        db.create_table('zeus_institution', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('ecounting_id', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('zeus', ['Institution'])


    def backwards(self, orm):
        # Adding model 'Faculty'
        db.create_table('zeus_faculty', (
            ('faculty_id', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('zeus', ['Faculty'])

        # Deleting model 'Institution'
        db.delete_table('zeus_institution')


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
        }
    }

    complete_apps = ['zeus']