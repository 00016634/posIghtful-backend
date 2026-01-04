from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserRole


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['id', 'username', 'email', 'full_name', 'phone_number', 'tenant', 'user_role', 'is_active', 'is_staff']
    list_filter = ['is_active', 'is_staff', 'tenant', 'user_role']
    search_fields = ['username', 'email', 'full_name', 'phone_number']
    ordering = ['username']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email', 'full_name', 'phone_number', 'tenant', 'user_role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'phone_number', 'tenant', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

    readonly_fields = ['created_at', 'updated_at', 'last_login', 'date_joined']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'description']
    search_fields = ['name', 'code']
