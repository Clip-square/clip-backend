from django.urls import path
from .views import OrganizationView, OrganizationInviteView

urlpatterns = [
    path("", OrganizationView.as_view()),
    path("<int:organization_id>/", OrganizationView.as_view()),
    path("invite/", OrganizationInviteView.as_view()),
]