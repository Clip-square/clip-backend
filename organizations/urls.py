from django.urls import path
from .views import OrganizationView, OrganizationDetailView, OrganizationInviteView
from meetings.views import MeetingCreateView

urlpatterns = [
    path("", OrganizationView.as_view()),
    path("<int:organization_id>/", OrganizationDetailView.as_view()),
    path("invite/", OrganizationInviteView.as_view()),
    path('<int:organization_id>/meetings/', MeetingCreateView.as_view()),
]