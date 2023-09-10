from django.contrib.auth.models import User
from django.db import models


class Geolocation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="geolocation")
    ip_address = models.CharField(max_length=24)
    geolocation = models.JSONField()
    signed_up_on_holiday = models.BooleanField(default=None)
