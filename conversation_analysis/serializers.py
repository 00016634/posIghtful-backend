from rest_framework import serializers
from .models import LeadConversation


class LeadConversationCreateSerializer(serializers.ModelSerializer):
    """Used when agents create a conversation (POST)."""

    class Meta:
        model = LeadConversation
        fields = [
            'id', 'lead', 'channel', 'audio_file', 'raw_transcript',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        channel = data.get('channel')
        audio_file = data.get('audio_file')
        raw_transcript = data.get('raw_transcript')

        if channel in ('email', 'online_chat') and not raw_transcript:
            raise serializers.ValidationError(
                "raw_transcript is required for email and online_chat channels."
            )

        if channel in ('in_person', 'phone') and not audio_file and not raw_transcript:
            raise serializers.ValidationError(
                "Either audio_file or raw_transcript is required for in_person and phone channels."
            )

        return data


class LeadConversationSerializer(serializers.ModelSerializer):
    """Full read serializer for supervisors/managers."""
    agent_code = serializers.CharField(source='agent.agent_code', read_only=True, default=None)
    agent_name = serializers.CharField(source='agent.user.full_name', read_only=True, default='')
    lead_customer_name = serializers.CharField(source='lead.customer_name', read_only=True, default='')
    lead_customer_phone = serializers.CharField(source='lead.customer_phone', read_only=True, default='')

    class Meta:
        model = LeadConversation
        fields = [
            'id', 'tenant', 'lead', 'agent', 'agent_code', 'agent_name',
            'lead_customer_name', 'lead_customer_phone',
            'channel', 'audio_file', 'raw_transcript',
            'transcription_status', 'analysis_status',
            'rating', 'conversation_topic', 'short_description',
            'conversation_outcome', 'customer_sentiment',
            'ai_raw_response', 'analyzed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'tenant', 'transcription_status', 'analysis_status',
            'rating', 'conversation_topic', 'short_description',
            'conversation_outcome', 'customer_sentiment',
            'ai_raw_response', 'analyzed_at', 'created_at', 'updated_at',
        ]
