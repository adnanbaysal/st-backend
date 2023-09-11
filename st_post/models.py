from django.contrib.auth.models import User
from django.db import models


class Post(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="posts")
    text = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
