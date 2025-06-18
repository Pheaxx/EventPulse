from django.contrib.auth.models import User
from django.db import models
import uuid

from .fields import EncryptedField

# Create your models here.
class RelaySettings(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.TextField()
    description = models.TextField()
    event_code = models.CharField(max_length=255)
    source_host = models.TextField()
    forward_url = models.TextField()
    api_key = EncryptedField(blank=True, null=True)
    api_secret = EncryptedField(blank=True, null=True)


class Events(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    relay_settings_fk= models.ManyToManyField(RelaySettings, blank=True)
    uuid = models.UUIDField(unique=True, db_index=True)
    processed = models.BooleanField(default=False)
    retry = models.BooleanField(default=False)
    host = models.TextField()
    isvalid_hmac = models.BooleanField(default=False)
    psp_reference = models.TextField()
    event_code = models.TextField()
    payload = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint("psp_reference", "event_code", name="psp_reference_event_code_idx")
        ]


class Log(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at =  models.DateTimeField(auto_now=True)
    uuid = models.UUIDField(db_index=True)
    level = models.CharField()
    message = models.JSONField()