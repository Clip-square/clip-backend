from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class UserManager(BaseUserManager):
    def create_user(self, email, password, name, **kwargs):
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(email = email, name = name)
        user.set_password(password)
        user.save(using = self._db)
        return user

    def create_superuser(self, email=None, password=None, name="Admin", **extra_fields):
        superuser = self.create_user(email = email, password = password, name = name)
        superuser.is_staff = True
        superuser.is_superuser = True
        superuser.is_active = True
        superuser.save(using = self._db)
        return superuser

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length = 320, unique = True, null = False, blank = False)
    name = models.CharField(max_length = 16, unique = False, null = False, blank = False)
    is_superuser = models.BooleanField(default = False)
    is_active = models.BooleanField(default = True)
    is_staff = models.BooleanField(default = False)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    
    def __str__(self):
        return self.email