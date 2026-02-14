from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import models


# ─── Role definitions ───────────────────────────────────────────

class Role(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    permissions = models.JSONField(
        default=dict, blank=True,
        help_text='e.g. {"leads": ["view","create","update"], "users": ["view"]}'
    )
    color = models.CharField(max_length=30, blank=True, default='blue')
    icon = models.CharField(max_length=50, blank=True, default='user')

    class Meta:
        db_table = 'roles'

    def __str__(self):
        return self.name


# ─── User manager ───────────────────────────────────────────────

class UserManager(BaseUserManager):
    def _create_user(self, username, email=None, phone_number=None, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        if email:
            email = self.normalize_email(email)
        user = self.model(username=username, email=email, phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, phone_number=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, phone_number, password, **extra_fields)

    def create_superuser(self, username, email=None, phone_number=None, password=None, **extra_fields):
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(username, email, phone_number, password, **extra_fields)


# ─── User ────────────────────────────────────────────────────────

class User(AbstractUser):
    tenant = models.ForeignKey(
        'tenancy.Tenant', on_delete=models.CASCADE,
        related_name='users', null=True, blank=True,
    )
    email = models.EmailField(null=True, blank=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)

    phone_number_regex = RegexValidator(regex=r'^(\+998|998)\d{9}$', message=_('Phone number Regex'))
    phone_number = models.CharField(
        validators=[phone_number_regex], max_length=50,
        unique=True, null=True, blank=True,
    )

    last_login_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'phone_number']

    class Meta:
        db_table = 'users'
        unique_together = [['tenant', 'email']]

    def clean(self):
        super().clean()
        if self.email and self.tenant:
            qs = User.objects.exclude(id=self.id).filter(tenant=self.tenant, email=self.email)
            if qs.exists():
                raise ValidationError('A user with this email already exists in this tenant.')

    def __str__(self):
        return self.username


# ─── User-Role assignment (per tenant) ──────────────────────────

class UserRole(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(
        'tenancy.Tenant', on_delete=models.CASCADE,
        related_name='user_roles',
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_roles'
        unique_together = [['tenant', 'user', 'role']]

    def __str__(self):
        return f"{self.user.username} – {self.role.name} ({self.tenant.code})"
