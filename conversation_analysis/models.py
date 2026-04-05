from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class LeadConversation(models.Model):
    CHANNEL_CHOICES = [
        ('in_person', 'In Person'),
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('online_chat', 'Online Chat'),
    ]

    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]

    SENTIMENT_CHOICES = [
        ('very_negative', 'Very Negative'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
        ('positive', 'Positive'),
        ('very_positive', 'Very Positive'),
    ]

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(
        'tenancy.Tenant', on_delete=models.CASCADE,
        related_name='lead_conversations',
    )
    lead = models.OneToOneField(
        'leads.Lead', on_delete=models.CASCADE,
        related_name='conversation',
    )
    agent = models.ForeignKey(
        'tenancy.Agent', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='conversations',
    )

    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)

    # Source data
    audio_file = models.FileField(
        upload_to='conversations/audio/%Y/%m/',
        null=True, blank=True,
        help_text='Voice recording for in_person/phone channels',
    )
    raw_transcript = models.TextField(
        null=True, blank=True,
        help_text='Chat transcript (uploaded) or transcribed from audio',
    )

    # Processing status
    transcription_status = models.CharField(
        max_length=20, choices=PROCESSING_STATUS_CHOICES, default='pending',
    )
    analysis_status = models.CharField(
        max_length=20, choices=PROCESSING_STATUS_CHOICES, default='pending',
    )

    # AI analysis results
    rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='AI-assigned agent performance rating (1-5 stars)',
    )
    conversation_topic = models.CharField(
        max_length=255, null=True, blank=True,
        help_text='AI-extracted main topic of the conversation',
    )
    short_description = models.TextField(
        null=True, blank=True,
        help_text='AI-generated brief summary of the conversation',
    )
    conversation_outcome = models.TextField(
        null=True, blank=True,
        help_text='AI-generated description of the conversation result',
    )
    customer_sentiment = models.CharField(
        max_length=20, choices=SENTIMENT_CHOICES,
        null=True, blank=True,
    )
    ai_raw_response = models.JSONField(
        null=True, blank=True,
        help_text='Full AI response for debugging/auditing',
    )

    analyzed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lead_conversations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'agent']),
            models.Index(fields=['tenant', 'customer_sentiment']),
            models.Index(fields=['tenant', 'rating']),
        ]

    def __str__(self):
        return f"Conversation for Lead {self.lead_id} ({self.channel})"
