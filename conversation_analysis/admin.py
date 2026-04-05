from django.contrib import admin
from .models import LeadConversation


@admin.register(LeadConversation)
class LeadConversationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'lead', 'agent', 'channel',
        'rating', 'customer_sentiment',
        'transcription_status', 'analysis_status',
        'created_at',
    ]
    list_filter = ['channel', 'customer_sentiment', 'rating', 'analysis_status', 'transcription_status']
    search_fields = ['lead__customer_name', 'conversation_topic', 'short_description']
    readonly_fields = [
        'rating', 'conversation_topic', 'short_description',
        'conversation_outcome', 'customer_sentiment', 'ai_raw_response',
        'analyzed_at', 'transcription_status', 'analysis_status',
    ]
    raw_id_fields = ['lead', 'agent', 'tenant']
