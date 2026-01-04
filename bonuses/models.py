from django.db import models


class BonusRuleSet(models.Model):
    """Collection of bonus rules for a specific period"""
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='bonus_rule_sets')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField(blank=True, null=True)
    valid_to = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'bonus_rule_sets'

    def __str__(self):
        return f"{self.name} ({self.tenant.code})"


class BonusRule(models.Model):
    """Individual bonus calculation rules"""
    PER_CONVERSION = 'per_conversion'
    PER_LEAD = 'per_lead'
    PER_TARGET = 'per_target'
    TIER = 'tier'

    RULE_TYPE_CHOICES = [
        (PER_CONVERSION, 'Per Conversion'),
        (PER_LEAD, 'Per Lead'),
        (PER_TARGET, 'Per Target'),
        (TIER, 'Tier'),
    ]

    FIXED = 'fixed'
    PERCENT_OF_SALE = 'percent_of_sale'

    AMOUNT_TYPE_CHOICES = [
        (FIXED, 'Fixed Amount'),
        (PERCENT_OF_SALE, 'Percent of Sale'),
    ]

    id = models.BigAutoField(primary_key=True)
    rule_set = models.ForeignKey(BonusRuleSet, on_delete=models.CASCADE, related_name='rules')
    rule_type = models.CharField(max_length=80, choices=RULE_TYPE_CHOICES)
    condition_expr = models.TextField(blank=True, null=True)  # JSON logic targeting lead/conversion fields
    amount_type = models.CharField(max_length=30, choices=AMOUNT_TYPE_CHOICES)
    amount_value = models.DecimalField(max_digits=18, decimal_places=4)
    cap_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)  # optional cap
    priority = models.IntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'bonus_rules'
        ordering = ['priority']

    def __str__(self):
        return f"{self.rule_type} - {self.amount_type} ({self.rule_set.name})"


class BonusCalculationRun(models.Model):
    """Bonus calculation execution records"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (RUNNING, 'Running'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
    ]

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='bonus_calc_runs')
    period_start = models.DateField()
    period_end = models.DateField()
    triggered_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='triggered_bonus_calcs')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'bonus_calculation_runs'

    def __str__(self):
        return f"Bonus Calc {self.id} - {self.period_start} to {self.period_end} ({self.status})"


class BonusCalculationItem(models.Model):
    """Individual bonus amounts calculated per agent/conversion"""
    id = models.BigAutoField(primary_key=True)
    calc_run = models.ForeignKey(BonusCalculationRun, on_delete=models.CASCADE, related_name='calculation_items')
    agent = models.ForeignKey('tenancy.Agent', on_delete=models.CASCADE, related_name='bonus_items')
    outlet = models.ForeignKey('tenancy.Outlet', on_delete=models.SET_NULL, null=True, blank=True, related_name='bonus_items')
    conversion = models.ForeignKey('conversions.Conversion', on_delete=models.SET_NULL, null=True, blank=True, related_name='bonus_items')
    lead = models.ForeignKey('leads.Lead', on_delete=models.SET_NULL, null=True, blank=True, related_name='bonus_items')
    applied_rule = models.ForeignKey(BonusRule, on_delete=models.SET_NULL, null=True, blank=True, related_name='calculated_items')
    gross_bonus = models.DecimalField(max_digits=18, decimal_places=2)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'bonus_calculation_items'

    def __str__(self):
        return f"Bonus {self.gross_bonus} for Agent {self.agent_id}"


class BonusPayoutExport(models.Model):
    """Track exported bonus payout files"""
    CSV = 'csv'
    PDF = 'pdf'
    XML = 'xml'

    EXPORT_FORMAT_CHOICES = [
        (CSV, 'CSV'),
        (PDF, 'PDF'),
        (XML, 'XML'),
    ]

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='bonus_exports')
    calc_run = models.ForeignKey(BonusCalculationRun, on_delete=models.CASCADE, related_name='exports')
    export_format = models.CharField(max_length=30, choices=EXPORT_FORMAT_CHOICES, blank=True, null=True)
    exported_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='bonus_exports')
    exported_at = models.DateTimeField(blank=True, null=True)
    file_path = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'bonus_payout_exports'

    def __str__(self):
        return f"Export {self.id} - {self.export_format} ({self.exported_at})"
