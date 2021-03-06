from django.shortcuts import render
from rest_framework.authentication import OAuth2Authentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status

from .serializers import CheckpointSerializer, RacerSerializer

from checkpoints.models import Checkpoint
from racers.models import Racer
from racecontrol.models import RaceControl
from raceentries.models import RaceEntry
from jobs.models import Job
from runs.models import Run
from racelogs.models import RaceLog

import datetime
import pytz

class AvailableCheckpointsView(APIView):
    
    authentication_classes = (OAuth2Authentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    
    def get(self, request, *args, **kwargs):
        checkpoints = request.user.authorized_checkpoints.all()
        serialized_checkpoints = CheckpointSerializer(checkpoints)
        return Response(serialized_checkpoints.data, status=status.HTTP_200_OK)
        

class PingView(APIView):
    authentication_classes = (OAuth2Authentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    
    def get(self, request, *args, **kwargs):
        current_race = RaceControl.shared_instance().current_race
        context = {
            'successful' : True,
            'current_race' : current_race.race_name,
            'race_start_time' : current_race.race_start_time
        }
        return Response(context, status=status.HTTP_200_OK)

class CheckpointIdentificationView(APIView):
    def post(self, request, *args, **kwargs):
        checkpoint_number = request.DATA['checkpoint']
        try:
            checkpoint = Checkpoint.objects.get(checkpoint_number=checkpoint_number)
            context = {
                'checkpoint_number' : checkpoint.checkpoint_number,
                'checkpoint_name' : checkpoint.checkpoint_name,
                'request_user' : request.user.username
            }
            return Response(context, status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class RacerDetailView(generics.RetrieveAPIView):
    authentication_classes = (OAuth2Authentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    
    serializer_class = RacerSerializer
    model = Racer
    lookup_field = 'racer_number'

class PickView(APIView):
    authentication_classes = (OAuth2Authentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, *args, **kwargs):
        current_race = RaceControl.shared_instance().current_race
        racer_number = request.DATA['racer_number']
        job_number = request.DATA['job_number']
        checkpoint = request.DATA['checkpoint']
        
        #Check for job number
        job_count = Job.objects.filter(job_id=job_number).filter(race=current_race).count()
        if job_count == 0:
            return Response({'confirm_code' : None, 'error' : True, 'error_title' : 'Cannot Find Job', 'error_description' : 'No job found with job number {}.'.format(str(job_number))}, status=status.HTTP_200_OK)
        
        #Job is valid, get the job.
        job = Job.objects.filter(job_id=job_number).filter(race=current_race).first()
        
        #Check to make sure racer is at right checkpoint
        if job.pick_checkpoint.pk != checkpoint:
            return Response({'confirm_code' : None, 'error' : True, 'error_title' : 'Wrong Checkpoint', 'error_description' : 'This pick up needs to be made at {}.'.format(str(job.pick_checkpoint.checkpoint_name))}, status=status.HTTP_200_OK)
                
        #Make sure the racer is entered in the race
        race_entry_count = RaceEntry.objects.filter(race=current_race).filter(racer__racer_number=racer_number).count()
        
        if race_entry_count == 0:
            return Response({'confirm_code' : None, 'error' : True, 'error_title' : 'Racer not entered in race.', 'error_description' : 'No racer found with racer number {} is entered in this race.'.format(str(racer_number))}, status=status.HTTP_200_OK)
        
        #Racer is in race, grab her/his race entry
        race_entry = RaceEntry.objects.filter(race=current_race).filter(racer__racer_number=racer_number).first()
        
        #Check to make sure Racer is not DQ'd
        if race_entry.entry_status == RaceEntry.ENTRY_STATUS_DQD:
            return Response({'confirm_code' : None, 'error' : True, 'error_title' : 'Racer has been Disqualified', 'error_description' : 'Race #{} has been disqualified from the race. Have the racer report to HQ if they have any questions.'.format(str(racer_number))}, status=status.HTTP_200_OK)
        
        #Check if Racer has done Job
        run_count = Run.objects.filter(job=job).filter(race_entry=race_entry).count()
        
        if run_count != 0:
            previous_run = Run.objects.filter(job=job).filter(race_entry=race_entry).first()
            return Response({'confirm_code' : None, 'error' : True, 'error_title' : 'Racer already did job.', 'error_description' : 'The racer has already done job {}, the confirm code was {}'.format(str(job_number), str(previous_run.pk))}, status=status.HTTP_200_OK)
        
        #Check if job is ready
        ready_time = current_race.race_start_time.astimezone(pytz.utc) + datetime.timedelta(minutes=job.minutes_ready_after_start)
        
        if datetime.datetime.now(tz=pytz.utc) <= ready_time:
            central = pytz.timezone('US/Central')
            ready_time_localized = ready_time.astimezone(central).strftime('%I:%M %p')
            return Response({'confirm_code' : None, 'error' : True, 'error_title' : 'Job is not ready yet.', 'error_description' : 'Job is ready until {}.'.format(ready_time_localized)}, status=status.HTTP_200_OK)
        
        #Check to see if job is still alive
        due_time = current_race.race_start_time.astimezone(pytz.utc) + datetime.timedelta(minutes=job.minutes_due_after_start)
        if datetime.datetime.now(tz=pytz.utc) > due_time:
            central = pytz.timezone('US/Central')
            due_time_localized = due_time.astimezone(central).strftime('%I:%M %p')
            return Response({'confirm_code' : None, 'error' : True, 'error_title' : 'Job is Dead.', 'error_description' : 'Job died at {}.'.format(due_time_localized)}, status=status.HTTP_200_OK)
        
        #All checks have passed, lets create the run
        run = Run()
        run.pick(job, race_entry)
        
        try:
            RaceLog(racer=race_entry.racer, race=race_entry.race, user=request.user, log="Racer picked up job #{}".format(str(job_number)), current_grand_total=race_entry.grand_total, current_number_of_runs=race_entry.number_of_runs_completed).save()
        except:
            pass
        
        return Response({'confirm_code' : run.pk, 'error' : False, 'error_title' : None, 'error_description' : None}, status=status.HTTP_200_OK)
        

class DropView(APIView):
    authentication_classes = (OAuth2Authentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, *args, **kwargs):
        current_race = RaceControl.shared_instance().current_race
        racer_number = request.DATA['racer_number']
        confirm_code = request.DATA['confirm_code']
        checkpoint = request.DATA['checkpoint']
        
        try:
            run = Run.objects.get(pk=confirm_code)
        except:
            return Response({'error' : True, 'error_title' : 'Cannot Find Confirm Code', 'error_description' : "No job's' drop off assoicated with confirm code {}.".format(str(confirm_code))}, status=status.HTTP_200_OK)
            
        #Make sure racer is authorized to make drop
        if run.race_entry.racer.racer_number != racer_number:
            return Response({'error' : True, 'error_title' : 'Wrong Racer #', 'error_description' : 'Racer # {} does not a drop off with confirm code {}.'.format(str(racer_number), str(confirm_code))}, status=status.HTTP_200_OK)

        #Check to make sure racer is at right checkpoint
        if run.job.drop_checkpoint.pk != checkpoint:
            return Response({'error' : True, 'error_title' : 'Wrong Checkpoint', 'error_description' : 'This drop off needs to be made at {}.'.format(str(run.job.drop_checkpoint.checkpoint_name))}, status=status.HTTP_200_OK)
                
        #Check to make sure Racer hasn't already dropped off job
        if run.status == Run.RUN_STATUS_COMPLETED:
            central = pytz.timezone('US/Central')
            drop_time_localized = run.utc_time_dropped.astimezone(central).strftime('%I:%M %p')
            return Response({'error' : True, 'error_title' : 'Job already dropped off', 'error_description' : 'The run was already dropped off at {}.'.format(str(drop_time_localized))}, status=status.HTTP_200_OK)
        
        run.drop()
        
        run.race_entry.add_up_points()
        run.race_entry.add_up_runs()
        run.race_entry.save()
        
        try:
            RaceLog(racer=run.race_entry.racer, race=run.race_entry.race, user=request.user, log="Racer dropped off job #{}".format(str(run.job.job_id)), current_grand_total=run.race_entry.grand_total, current_number_of_runs=run.race_entry.number_of_runs_completed).save()
        except:
            pass
        
        return Response({'error' : False, 'error_title' : None, 'error_description' : None}, status=status.HTTP_200_OK)