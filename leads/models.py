from django.db import models


# ─── Pipeline & stages ───────────────────────────────────────────

class LeadPipeline(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='lead_pipelines')
    product = models.ForeignKey('tenancy.Product', on_delete=models.CASCADE, related_name='pipelines')
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'lead_pipelines'
        unique_together = [['tenant', 'product', 'name']]

    def __str__(self):
        return f"{self.name} ({self.product.name})"


class LeadStage(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='lead_stages')
    pipeline = models.ForeignKey(LeadPipeline, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=120)
    stage_order = models.IntegerField()
    is_terminal = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'lead_stages'
        unique_together = [['tenant', 'pipeline', 'stage_order']]
        indexes = [
            models.Index(fields=['tenant', 'pipeline', 'name']),
        ]
        ordering = ['stage_order']

    def __str__(self):
        return f"{self.pipeline.name} → {self.name} (#{self.stage_order})"


# ─── Lead (umbrella) ────────────────────────────────────────────

class Lead(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='leads')
    agent = models.ForeignKey('tenancy.Agent', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    customer = models.ForeignKey('tenancy.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')

    interaction_type = models.CharField(max_length=80, blank=True, null=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_phone = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    primary_application = models.ForeignKey(
        'LeadApplication', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )

    server_received_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'leads'

    def __str__(self):
        return f"Lead {self.id} – {self.customer_name or 'Unnamed'}"


# ─── Lead applications (per-product attempts) ───────────────────

class LeadApplication(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='lead_applications')
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='applications')

    product = models.ForeignKey('tenancy.Product', on_delete=models.CASCADE, related_name='lead_applications')
    pipeline = models.ForeignKey(LeadPipeline, on_delete=models.CASCADE, related_name='applications')
    app_id = models.CharField(max_length=120, blank=True, null=True)

    current_stage = models.ForeignKey(LeadStage, on_delete=models.CASCADE, related_name='current_applications')
    status_last_updated_at = models.DateTimeField(blank=True, null=True)
    last_stage_history = models.ForeignKey(
        'LeadStageHistory', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )

    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'lead_applications'

    def __str__(self):
        return f"App {self.app_id or self.id} – Lead {self.lead_id} ({self.product.name})"


# ─── Stage history ───────────────────────────────────────────────

class LeadStageHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='lead_stage_history')

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='stage_history')
    lead_application = models.ForeignKey(LeadApplication, on_delete=models.CASCADE, related_name='stage_history')

    from_stage = models.ForeignKey(LeadStage, on_delete=models.SET_NULL, null=True, blank=True, related_name='history_from')
    to_stage = models.ForeignKey(LeadStage, on_delete=models.CASCADE, related_name='history_to')
    changed_at = models.DateTimeField()
    note = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'lead_stage_history'
        indexes = [
            models.Index(fields=['tenant', 'lead_application', 'changed_at']),
        ]

    def __str__(self):
        return f"App {self.lead_application_id}: {self.from_stage} → {self.to_stage}"
