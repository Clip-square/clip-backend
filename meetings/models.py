from django.db import models
from accounts.models import CustomUser
from organizations.models import Organization

class Meeting(models.Model):
    title = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    total_duration = models.DurationField()
    meeting_minutes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False)
    is_paused = models.BooleanField(default=False)

    attendees = models.ManyToManyField(CustomUser, through='MeetingParticipant')
    organization = models.ForeignKey(Organization, related_name="meetings", on_delete=models.CASCADE)


    def __str__(self):
        return self.title


class Section(models.Model):
    meeting = models.ForeignKey(Meeting, related_name='sections', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    duration = models.DurationField()
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.meeting.title} - {self.name}"


class MeetingParticipant(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    has_joined = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.meeting.title}"
