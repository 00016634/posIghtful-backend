from django.contrib import admin
from .models import Tenant, Region, Outlet, Agent


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code']


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'tenant', 'is_active']
    list_filter = ['is_active', 'tenant']
    search_fields = ['name', 'code']


@admin.register(Outlet)
class OutletAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'outlet_type', 'region', 'tenant', 'is_active']
    list_filter = ['outlet_type', 'is_active', 'tenant', 'region']
    search_fields = ['name', 'code', 'address']


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['id', 'agent_code', 'user', 'outlet', 'status', 'hired_at', 'tenant']
    list_filter = ['status', 'tenant', 'outlet', 'hired_at']
    search_fields = ['agent_code', 'user__email']
