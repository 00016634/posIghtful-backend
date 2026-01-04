from django.db import models
import uuid


class Campaign(models.Model):
    """Marketing campaigns"""
    PLANNED = 'planned'
    ACTIVE = 'active'
    ENDED = 'ended'

    STATUS_CHOICES = [
        (PLANNED, 'Planned'),
        (ACTIVE, 'Active'),
        (ENDED, 'Ended'),
    ]

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='campaigns')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'campaigns'

    def __str__(self):
        return f"{self.name} ({self.code or 'No Code'})"


class AttributionSource(models.Model):
    """Lead attribution sources (walk-in, partner, street team, etc.)"""
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=80, unique=True)  # walk_in, partner_outlet, street_team
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'attribution_sources'

    def __str__(self):
        return self.name


class Lead(models.Model):
    """Customer leads captured by agents"""
    NEW = 'new'
    QUALIFIED = 'qualified'
    REJECTED = 'rejected'
    CONVERTED = 'converted'
    EXPIRED = 'expired'

    STATUS_CHOICES = [
        (NEW, 'New'),
        (QUALIFIED, 'Qualified'),
        (REJECTED, 'Rejected'),
        (CONVERTED, 'Converted'),
        (EXPIRED, 'Expired'),
    ]

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='leads')
    lead_uuid = models.UUIDField(default=uuid.uuid4)  # for idempotent insert from devices
    agent = models.ForeignKey('tenancy.Agent', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    outlet = models.ForeignKey('tenancy.Outlet', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    attribution_source = models.ForeignKey(AttributionSource, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_phone = models.CharField(max_length=100, blank=True, null=True)
    customer_doc_id = models.CharField(max_length=150, blank=True, null=True)  # passport/ID
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=NEW)
    potential_product = models.CharField(max_length=150, blank=True, null=True)  # product agent pitched
    captured_at = models.DateTimeField()
    server_received_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    is_deduplicated = models.BooleanField(default=False)  # true if merged on server
    dedup_master_lead = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='duplicates')
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'leads'

    def __str__(self):
        return f"Lead {self.id} - {self.customer_name or 'Unnamed'} ({self.status})"


class LeadInteraction(models.Model):
    """Track agent interactions with leads"""
    CALL = 'call'
    VISIT = 'visit'
    REMINDER = 'reminder'
    VERIFICATION = 'verification'

    INTERACTION_TYPE_CHOICES = [
        (CALL, 'Call'),
        (VISIT, 'Visit'),
        (REMINDER, 'Reminder'),
        (VERIFICATION, 'Verification'),
    ]

    id = models.BigAutoField(primary_key=True)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='interactions')
    agent = models.ForeignKey('tenancy.Agent', on_delete=models.SET_NULL, null=True, blank=True, related_name='lead_interactions')
    interaction_type = models.CharField(max_length=80, choices=INTERACTION_TYPE_CHOICES, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    next_action_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lead_interactions'

    def __str__(self):
        return f"{self.interaction_type or 'Interaction'} for Lead {self.lead_id}"


class LeadStatusHistory(models.Model):
    """Audit trail for lead status changes"""
    id = models.BigAutoField(primary_key=True)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=30, blank=True, null=True)
    new_status = models.CharField(max_length=30)
    changed_by_user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='lead_status_changes')
    changed_at = models.DateTimeField()
    reason = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'lead_status_history'

    def __str__(self):
        return f"Lead {self.lead_id}: {self.old_status} → {self.new_status}"
