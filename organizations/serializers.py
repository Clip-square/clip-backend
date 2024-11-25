from rest_framework import serializers
from .models import Organization, OrganizationMember
from accounts.serializers import UserSerializer

class OrganizationSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Organization
        fields = ['id', 'name', 'owner', 'invite_code', 'created_at', 'members']

class OrganizationMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = OrganizationMember
        fields = ['id', 'organization', 'user', 'joined_at']
