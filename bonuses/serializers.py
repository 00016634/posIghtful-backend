from rest_framework import serializers
from .models import CommissionPolicy, BonusRule, BonusLedger


class CommissionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionPolicy
        fields = [
            'id', 'tenant', 'name', 'mode', 'window_interval',
            'effective_from', 'effective_to', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


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
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class BonusLedgerSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source='agent.user.full_name', read_only=True, default='')
    agent_code = serializers.CharField(source='agent.agent_code', read_only=True, default='')
    rule_name = serializers.CharField(source='rule.name', read_only=True, default=None)
    sale_amount = serializers.DecimalField(source='sale.amount', max_digits=18, decimal_places=2, read_only=True)
    sale_date = serializers.DateTimeField(source='sale.sold_at', read_only=True)

    class Meta:
        model = BonusLedger
        fields = [
            'id', 'tenant', 'sale', 'agent', 'rule',
            'agent_name', 'agent_code', 'rule_name',
            'sale_amount', 'sale_date',
            'bonus_amount', 'calculation_detail', 'created_at',
        ]
        read_only_fields = fields
