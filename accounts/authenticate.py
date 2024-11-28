from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.conf import settings
from django.shortcuts import get_object_or_404
from .models import CustomUser
import jwt
import logging


logger = logging.getLogger(__name__)

class SafeJWTAuthentication(BaseAuthentication):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SafeJWTAuthentication, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def authenticate(self, request):
        logger.info("Authenticating request...")
        
        access_token = request.COOKIES.get("access", None)
        logger.debug(f"Access token from cookies: {access_token}")

        if not access_token:
            logger.warning("No access token found in cookies.")
            return (None, None)

        try:
            payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
            logger.debug(f"Decoded payload: {payload}")
            
            user_id = payload.get("user_id")
            logger.info(f"User ID from token: {user_id}")

            user = self.authenticate_credentials(user_id)
            return (user, None)

        except jwt.ExpiredSignatureError:
            logger.error("Access token has expired.")
            raise exceptions.AuthenticationFailed("Access token expired.")
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise exceptions.AuthenticationFailed("Invalid token.")

    def authenticate_credentials(self, user_id):
        logger.info(f"Authenticating user with ID: {user_id}")

        try:
            user = get_object_or_404(CustomUser, pk=user_id)
            logger.info(f"User found: {user}")
        except Exception as e:
            logger.error(f"Error fetching user: {e}")
            raise exceptions.AuthenticationFailed("User not found.")

        if not user.is_active:
            logger.warning("User account is inactive.")
            raise exceptions.AuthenticationFailed("User is inactive.")

        return user
