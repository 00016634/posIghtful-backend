from rest_framework import serializers
from .models import LeadPipeline, LeadStage, Lead, LeadApplication, LeadStageHistory


class LeadPipelineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = LeadPipeline
        fields = ['id', 'tenant', 'product', 'product_name', 'name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeadStageSerializer(serializers.ModelSerializer):
    pipeline_name = serializers.CharField(source='pipeline.name', read_only=True)

    class Meta:
        model = LeadStage
        fields = [
            'id', 'tenant', 'pipeline', 'pipeline_name', 'name',
            'stage_order', 'is_terminal', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeadStageHistorySerializer(serializers.ModelSerializer):
    from_stage_name = serializers.CharField(source='from_stage.name', read_only=True, default=None)
    to_stage_name = serializers.CharField(source='to_stage.name', read_only=True)

    class Meta:
        model = LeadStageHistory
        fields = [
            'id', 'tenant', 'lead', 'lead_application',
            'from_stage', 'from_stage_name', 'to_stage', 'to_stage_name',
            'changed_at', 'note',
        ]
        read_only_fields = ['id']


class LeadApplicationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    current_stage_name = serializers.CharField(source='current_stage.name', read_only=True)

    class Meta:
        model = LeadApplication
        fields = [
            'id', 'tenant', 'lead', 'product', 'product_name',
            'pipeline', 'app_id', 'current_stage', 'current_stage_name',
            'status_last_updated_at', 'is_primary', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeadSerializer(serializers.ModelSerializer):
    agent_code = serializers.CharField(source='agent.agent_code', read_only=True, default=None)
    applications = LeadApplicationSerializer(many=True, read_only=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'tenant', 'agent', 'agent_code', 'customer',
            'interaction_type', 'customer_name', 'customer_phone',
            'latitude', 'longitude', 'primary_application',
            'server_received_at', 'created_at', 'updated_at',
            'applications',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
