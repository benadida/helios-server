# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Institution'
        db.create_table(u'heliosinstitution_institution', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('main_phone', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('sec_phone', self.gf('django.db.models.fields.CharField')(max_length=25, blank=True)),
            ('address', self.gf('django.db.models.fields.TextField')(max_length=250)),
            ('mngt_email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
        ))
        db.send_create_signal(u'heliosinstitution', ['Institution'])


    def backwards(self, orm):
        # Deleting model 'Institution'
        db.delete_table(u'heliosinstitution_institution')


    models = {
        u'heliosinstitution.institution': {
            'Meta': {'object_name': 'Institution'},
            'address': ('django.db.models.fields.TextField', [], {'max_length': '250'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'main_phone': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'mngt_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'sec_phone': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'})
        }
    }

    complete_apps = ['heliosinstitution']