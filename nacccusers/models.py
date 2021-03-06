from django.db import models
from django.contrib.auth.models import AbstractUser
from checkpoints.models import Checkpoint

class NACCCUser(AbstractUser):
    authorized_checkpoints = models.ManyToManyField(Checkpoint, blank=True)
