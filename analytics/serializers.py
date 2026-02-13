from rest_framework import serializers
from .models import KPIAgentDaily


class KPIAgentDailySerializer(serializers.ModelSerializer):
    agent_code = serializers.CharField(source='agent.agent_code', read_only=True, default=None)

    class Meta:
        model = KPIAgentDaily
        fields = [
            'id', 'tenant', 'agent', 'agent_code', 'kpi_date',
            'leads_captured', 'leads_converted', 'conversion_rate',
            'revenue_amount', 'bonus_amount', 'net_profit',
            'avg_time_to_convert', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
