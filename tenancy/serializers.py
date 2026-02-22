from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Tenant, Region, City, Product, Customer, Agent, SubscriptionPlan


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


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'price', 'description', 'max_agents', 'storage_limit', 'features', 'is_active']


class OnboardingSerializer(serializers.Serializer):
    # Step 1: Plan selection
    plan_id = serializers.IntegerField()

    # Step 2: Payment info (card_number and cvv are write_only, never stored)
    card_number = serializers.CharField(write_only=True, min_length=13, max_length=19)
    cardholder_name = serializers.CharField(max_length=255)
    expiry = serializers.CharField(max_length=5)
    cvv = serializers.CharField(write_only=True, min_length=3, max_length=4)
    billing_email = serializers.EmailField()

    # Step 3: Company info
    company_name = serializers.CharField(max_length=255)
    company_size = serializers.CharField(max_length=20)
    industry = serializers.CharField(max_length=50)

    # Step 3: Admin account
    admin_full_name = serializers.CharField(max_length=255)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_plan_id(self, value):
        if not SubscriptionPlan.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError('Invalid or inactive plan.')
        return value

    def validate_card_number(self, value):
        digits = value.replace(' ', '').replace('-', '')
        if not digits.isdigit() or len(digits) < 13:
            raise serializers.ValidationError('Invalid card number.')
        return digits

    def validate_expiry(self, value):
        import re
        if not re.match(r'^(0[1-9]|1[0-2])/\d{2}$', value):
            raise serializers.ValidationError('Expiry must be MM/YY format.')
        return value

    def validate_admin_email(self, value):
        from users.models import User
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value
