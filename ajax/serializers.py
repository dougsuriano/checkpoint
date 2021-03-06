from rest_framework import serializers

from racers.models import Racer
from raceentries.models import RaceEntry
from jobs.models import Job
from checkpoints.models import Checkpoint

class RacerSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='display_name')
    category_as_string = serializers.CharField(source='category_as_string')
    class Meta:
        model = Racer
        fields = ('racer_number', 'first_name', 'last_name', 'nick_name', 'city', 'gender', 'category', 'display_name', 'category_as_string')

class RaceEntrySerializer(serializers.ModelSerializer):
    entry_status_as_string = serializers.CharField(source='entry_status_as_string')
    racer = RacerSerializer()
    class Meta:
        model = RaceEntry
        depth = 2

class CheckpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = Checkpoint

class JobSerializer(serializers.ModelSerializer):
    pick_checkpoint = CheckpointSerializer()
    drop_checkpoint = CheckpointSerializer()
    class Meta:
        model = Job
        depth = 2