from django.contrib import admin
from .models import Campaign, AttributionSource, Lead, LeadInteraction, LeadStatusHistory


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'status', 'start_date', 'end_date', 'tenant']
    list_filter = ['status', 'tenant', 'start_date']
    search_fields = ['name', 'code']


@admin.register(AttributionSource)
class AttributionSourceAdmin(admin.ModelAdmin):
    list_display = ['id', 'code', 'name']
    search_fields = ['code', 'name']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'customer_phone', 'status', 'agent', 'outlet', 'captured_at']
    list_filter = ['status', 'tenant', 'outlet', 'campaign', 'attribution_source']
    search_fields = ['customer_name', 'customer_phone', 'customer_doc_id', 'lead_uuid']
    readonly_fields = ['lead_uuid', 'server_received_at', 'created_at', 'updated_at']


@admin.register(LeadInteraction)
class LeadInteractionAdmin(admin.ModelAdmin):
    list_display = ['id', 'lead', 'interaction_type', 'agent', 'created_at', 'next_action_at']
    list_filter = ['interaction_type', 'created_at']
    search_fields = ['lead__customer_name', 'notes']


@admin.register(LeadStatusHistory)
class LeadStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'lead', 'old_status', 'new_status', 'changed_by_user', 'changed_at']
    list_filter = ['old_status', 'new_status', 'changed_at']
    search_fields = ['lead__customer_name', 'reason']
