from rest_framework import serializers
from .models import Sale


class SaleSerializer(serializers.ModelSerializer):
    agent_code = serializers.CharField(source='agent.agent_code', read_only=True, default=None)
    product_name = serializers.CharField(source='product.name', read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True, default=None)

    class Meta:
        model = Sale
        fields = [
            'id', 'tenant', 'lead', 'lead_application',
            'customer', 'customer_name', 'agent', 'agent_code',
            'product', 'product_name', 'amount', 'status',
            'sold_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
