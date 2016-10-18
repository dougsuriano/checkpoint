# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'RaceControl'
        db.create_table(u'racecontrol_racecontrol', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('current_race', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['races.Race'], null=True, blank=True)),
        ))
        db.send_create_signal(u'racecontrol', ['RaceControl'])


    def backwards(self, orm):
        # Deleting model 'RaceControl'
        db.delete_table(u'racecontrol_racecontrol')


    models = {
        u'racecontrol.racecontrol': {
            'Meta': {'object_name': 'RaceControl'},
            'current_race': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['races.Race']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'races.race': {
            'Meta': {'object_name': 'Race'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'race_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'race_start_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'race_type': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'time_limit': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['racecontrol']