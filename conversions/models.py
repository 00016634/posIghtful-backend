from django.db import models


class Conversion(models.Model):
    """Successful conversions from leads to sales"""
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='conversions')
    lead = models.ForeignKey('leads.Lead', on_delete=models.SET_NULL, null=True, blank=True, related_name='conversions')
    agent = models.ForeignKey('tenancy.Agent', on_delete=models.SET_NULL, null=True, blank=True, related_name='conversions')
    outlet = models.ForeignKey('tenancy.Outlet', on_delete=models.SET_NULL, null=True, blank=True, related_name='conversions')
    campaign = models.ForeignKey('leads.Campaign', on_delete=models.SET_NULL, null=True, blank=True, related_name='conversions')
    external_sale_id = models.CharField(max_length=200, blank=True, null=True)  # ID from external POS/CRM
    sale_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    sale_currency = models.CharField(max_length=10, default='UZS')
    cost_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)  # acquisition cost
    converted_at = models.DateTimeField()
    source_system = models.CharField(max_length=100, blank=True, null=True)  # api_import, manual_upload
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'conversions'

    def __str__(self):
        return f"Conversion {self.id} - {self.sale_amount} {self.sale_currency}"


class ExternalImportBatch(models.Model):
    """Track external data import batches"""
    PENDING = 'pending'
    PROCESSED = 'processed'
    FAILED = 'failed'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSED, 'Processed'),
        (FAILED, 'Failed'),
    ]

    SALES = 'sales'
    COSTS = 'costs'
    AGENTS = 'agents'

    IMPORT_TYPE_CHOICES = [
        (SALES, 'Sales'),
        (COSTS, 'Costs'),
        (AGENTS, 'Agents'),
    ]

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='import_batches')
    source_system = models.CharField(max_length=100)  # "1C", "SAP", "custom_pos"
    import_type = models.CharField(max_length=50, choices=IMPORT_TYPE_CHOICES)
    file_name = models.CharField(max_length=300, blank=True, null=True)
    imported_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='imports')
    imported_at = models.DateTimeField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, blank=True, null=True)
    message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'external_import_batches'

    def __str__(self):
        return f"{self.source_system} - {self.import_type} ({self.status})"


class ExternalSalesImport(models.Model):
    """Individual sales records from external imports"""
    id = models.BigAutoField(primary_key=True)
    batch = models.ForeignKey(ExternalImportBatch, on_delete=models.CASCADE, related_name='sales_records')
    external_sale_id = models.CharField(max_length=200)
    outlet_code = models.CharField(max_length=100, blank=True, null=True)
    agent_code = models.CharField(max_length=100, blank=True, null=True)
    sale_date = models.DateField(blank=True, null=True)
    sale_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    cost_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    matched_conversion = models.ForeignKey(Conversion, on_delete=models.SET_NULL, null=True, blank=True, related_name='import_records')
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        db_table = 'external_sales_import'

    def __str__(self):
        return f"Sale {self.external_sale_id} - {self.sale_amount} {self.currency}"


class LedgerEntry(models.Model):
    """Financial ledger for revenue, cost, and bonus tracking"""
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='ledger_entries')
    outlet = models.ForeignKey('tenancy.Outlet', on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    agent = models.ForeignKey('tenancy.Agent', on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    conversion = models.ForeignKey(Conversion, on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    entry_date = models.DateField()
    revenue_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    cost_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    bonus_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)  # revenue - cost - bonus
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        db_table = 'ledger_entries'

    def save(self, *args, **kwargs):
        # Auto-calculate net profit
        self.net_profit = self.revenue_amount - self.cost_amount - self.bonus_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ledger {self.id} - {self.entry_date} - Net: {self.net_profit}"
