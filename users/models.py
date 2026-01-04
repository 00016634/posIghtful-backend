from django.db import models

import os
from uuid import uuid4
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError




class UserManager(BaseUserManager):
    def _create_user(self, username, email=None, phone_number=None, password=None, **extra_fields):
        """Create and save a User with the given username, email, phone and password."""
        if not username:
            raise ValueError('The Username field must be set')

        if email:
            email = self.normalize_email(email)

        user = self.model(username=username, email=email, phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, phone_number=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, email, phone_number, password, **extra_fields)

    def create_superuser(self, username, email=None, phone_number=None, password=None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(username, email, phone_number, password, **extra_fields)



class UserRole(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    description = models.TextField(max_length=500)

    def __str__(self) -> str:
        return f"{self.name}"



class User(AbstractUser):

    user_role = models.ForeignKey("users.UserRole", on_delete=models.SET_NULL, related_name="role", null=True, blank=True)

    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='tenant_users', null=True, blank=True)

    email = models.EmailField(null=True, blank=True)

    full_name = models.CharField(max_length=255, blank=True, null=True)

    phone_number_regex = RegexValidator(regex=r"^(\+998|998)\d{9}$", message=_("Phone number Regex"))

    phone_number = models.CharField(validators=[phone_number_regex], max_length=16, unique=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'phone_number']

    class Meta:
        db_table = "users"

    def clean(self):
        super().clean()
        if self.email: 
            if User.objects.exclude(id=self.id).filter(email=self.email).exists():
                raise ValidationError('A user with this email already exists.')
