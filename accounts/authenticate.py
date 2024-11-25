from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.conf import settings
from django.shortcuts import get_object_or_404
from .models import CustomUser
import jwt

class SafeJWTAuthentication(BaseAuthentication):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SafeJWTAuthentication, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def authenticate(self, request):
        access_token = request.COOKIES.get("access", None)
        if not access_token:
            return (None, None)

        try:
            payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")

            user = self.authenticate_credentials(user_id)
            return (user, None)

        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Access token expired.")
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid token.")

    def authenticate_credentials(self, user_id):
        user = get_object_or_404(CustomUser, pk=user_id)
        
        if not user.is_active:
            raise exceptions.AuthenticationFailed("User is inactive.")

        return user
