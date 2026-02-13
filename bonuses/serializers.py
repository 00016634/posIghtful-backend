from rest_framework import serializers
from .models import CommissionPolicy, BonusRule


class CommissionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionPolicy
        fields = [
            'id', 'tenant', 'name', 'mode', 'window_interval',
            'effective_from', 'effective_to', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BonusRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonusRule
        fields = [
            'id', 'tenant', 'name', 'is_active',
            'rule_dimension', 'operator',
            'ts_from', 'ts_to', 'num_from', 'num_to',
            'interval_from', 'interval_to', 'text_values', 'text_value',
            'amount_type', 'amount_value', 'cap_amount',
            'effective_from', 'effective_to',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
