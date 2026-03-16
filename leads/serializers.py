from rest_framework import serializers
from .models import LeadPipeline, LeadStage, Lead, LeadApplication, LeadStageHistory


class LeadPipelineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = LeadPipeline
        fields = ['id', 'tenant', 'product', 'product_name', 'name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class LeadStageSerializer(serializers.ModelSerializer):
    pipeline_name = serializers.CharField(source='pipeline.name', read_only=True)

    class Meta:
        model = LeadStage
        fields = [
            'id', 'tenant', 'pipeline', 'pipeline_name', 'name',
            'stage_order', 'is_terminal', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


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
        read_only_fields = ['id', 'tenant']


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
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class LeadSerializer(serializers.ModelSerializer):
    agent_code = serializers.CharField(source='agent.agent_code', read_only=True, default=None)
    agent_name = serializers.CharField(source='agent.user.full_name', read_only=True, default='')
    applications = LeadApplicationSerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()
    sale_amount = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'id', 'tenant', 'agent', 'agent_code', 'agent_name', 'customer',
            'interaction_type', 'customer_name', 'customer_phone',
            'latitude', 'longitude', 'primary_application',
            'server_received_at', 'created_at', 'updated_at',
            'applications', 'status', 'sale_amount',
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']

    def get_status(self, obj):
        app = obj.applications.filter(is_primary=True).first()
        if not app:
            app = obj.applications.first()
        if not app or not app.current_stage:
            return 'new'
        stage_name = app.current_stage.name.lower()
        if 'won' in stage_name or 'completed' in stage_name:
            return 'converted'
        elif 'lost' in stage_name or 'cancelled' in stage_name:
            return 'lost'
        elif 'new' in stage_name or 'requested' in stage_name:
            return 'new'
        else:
            return 'pending'

    def get_sale_amount(self, obj):
        from conversions.models import Sale
        sale = Sale.objects.filter(lead=obj, status='completed').first()
        if sale:
            return float(sale.amount)
        return None
