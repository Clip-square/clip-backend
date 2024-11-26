from django.urls import path
from .views import OrganizationView, OrganizationDetailView, OrganizationInviteView

urlpatterns = [
    path("", OrganizationView.as_view()),
    path("<int:organization_id>/", OrganizationDetailView.as_view()),
    path("invite/", OrganizationInviteView.as_view()),
]