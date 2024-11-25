from django.urls import path
from .consumers import MeetingConsumer

websocket_urlpatterns = [
    path("ws/meeting/<str:meeting_id>/", MeetingConsumer.as_asgi()),
]