from rest_framework import serializers
from .models import Tenant, Region, City, Product, Customer, Agent


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'code', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'tenant', 'name', 'code', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CitySerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = City
        fields = ['id', 'tenant', 'region', 'region_name', 'name', 'code', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'tenant', 'code', 'name', 'category', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'tenant', 'user', 'full_name', 'phone', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AgentSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True, default='')
    region_name = serializers.CharField(source='region.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    parent_code = serializers.CharField(source='parent.agent_code', read_only=True, default=None)

    class Meta:
        model = Agent
        fields = [
            'id', 'tenant', 'user', 'user_full_name', 'parent', 'parent_code',
            'agent_code', 'region', 'region_name', 'city', 'city_name',
            'hired_at', 'terminated_at', 'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
