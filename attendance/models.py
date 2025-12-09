from django.db import models
from django.contrib.auth.models import User
import datetime

class DriveToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Token for {self.user.username}"

# --- THIS WAS MISSING ---
class CompanySettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    late_threshold = models.TimeField(default=datetime.time(10, 0)) 

    def __str__(self):
        return f"Settings for {self.user.username}"