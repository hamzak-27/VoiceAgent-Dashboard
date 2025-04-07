from django.db import models
from django.utils import timezone

class Call(models.Model):
    phone_number = models.CharField(max_length=20)
    duration = models.IntegerField(help_text="Duration in seconds")
    call_time = models.DateTimeField(default=timezone.now)
    follow_up = models.BooleanField(default=False)
    summary = models.TextField(blank=True, null=True)
    transcript = models.TextField(blank=True, null=True)
    recording_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"Call to {self.phone_number} at {self.call_time}"

    class Meta:
        ordering = ['-call_time']