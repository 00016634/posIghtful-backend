from django.contrib import admin
from .models import Tenant, Region, City, Product, Customer, Agent


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


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'region', 'tenant', 'is_active']
    list_filter = ['is_active', 'tenant', 'region']
    search_fields = ['name', 'code']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'category', 'tenant', 'is_active']
    list_filter = ['is_active', 'tenant', 'category']
    search_fields = ['name', 'code']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'phone', 'tenant', 'created_at']
    list_filter = ['tenant']
    search_fields = ['full_name', 'phone']


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['id', 'agent_code', 'user', 'region', 'city', 'status', 'hired_at', 'tenant']
    list_filter = ['status', 'tenant', 'region', 'city', 'hired_at']
    search_fields = ['agent_code', 'user__email']
