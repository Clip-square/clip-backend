from .models import CustomUser
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        exclude = ['last_login', 'groups', 'user_permissions']

    def create(self, validated_data):
        password = validated_data['password']
        
        try:
            validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})
        
        user = CustomUser.objects.create_user(
            email = validated_data['email'],
            password = password,
            name = validated_data['name']
        )
        return user