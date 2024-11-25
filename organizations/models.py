from django.db import models
from accounts.models import CustomUser
from django.utils.crypto import get_random_string

class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    owner = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="owned_organizations",
    )
    invite_code = models.CharField(max_length=10, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = get_random_string(6)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class OrganizationMember(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="members"
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="organizations"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('organization', 'user')

    def __str__(self):
        return f"{self.user.name} in {self.organization.name}"
