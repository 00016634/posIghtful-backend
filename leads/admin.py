from django.contrib import admin
from .models import LeadPipeline, LeadStage, Lead, LeadApplication, LeadStageHistory


@admin.register(LeadPipeline)
class LeadPipelineAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'product', 'tenant', 'is_active']
    list_filter = ['is_active', 'tenant']
    search_fields = ['name']


@admin.register(LeadStage)
class LeadStageAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'pipeline', 'stage_order', 'is_terminal', 'is_active']
    list_filter = ['is_active', 'is_terminal', 'pipeline']
    search_fields = ['name']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'customer_phone', 'agent', 'interaction_type', 'created_at']
    list_filter = ['tenant', 'interaction_type']
    search_fields = ['customer_name', 'customer_phone']
    readonly_fields = ['server_received_at', 'created_at', 'updated_at']


@admin.register(LeadApplication)
class LeadApplicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'lead', 'product', 'pipeline', 'app_id', 'current_stage', 'is_primary']
    list_filter = ['tenant', 'is_primary', 'product', 'pipeline']
    search_fields = ['app_id']


@admin.register(LeadStageHistory)
class LeadStageHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'lead', 'lead_application', 'from_stage', 'to_stage', 'changed_at']
    list_filter = ['changed_at']
    search_fields = ['lead__customer_name', 'note']
