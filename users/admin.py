from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, UserRole


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['id', 'username', 'email', 'full_name', 'phone_number', 'tenant', 'is_active', 'is_staff']
    list_filter = ['is_active', 'is_staff', 'tenant']
    search_fields = ['username', 'email', 'full_name', 'phone_number']
    ordering = ['username']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email', 'full_name', 'phone_number', 'tenant')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'last_login_at', 'date_joined', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'phone_number', 'tenant', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

    readonly_fields = ['created_at', 'updated_at', 'last_login', 'last_login_at', 'date_joined']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'code', 'name', 'description']
    search_fields = ['name', 'code']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'tenant', 'user', 'role', 'assigned_at']
    list_filter = ['tenant', 'role']
    search_fields = ['user__username', 'role__name']
