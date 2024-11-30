from django.urls import path
from .views import MeetingView, MeetingDetailView, MeetingStatusUpdateView

urlpatterns = [
    path("", MeetingView.as_view()),
    path("<int:meeting_id>/", MeetingDetailView.as_view()),
    path("status/<int:meeting_id>/", MeetingStatusUpdateView.as_view())
]