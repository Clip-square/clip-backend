from django.urls import path
from .views import MeetingView, MeetingDetailView

urlpatterns = [
    path("", MeetingView.as_view()),
    path("<int:meeting_id>/", MeetingDetailView.as_view()),
]