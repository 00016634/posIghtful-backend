from django.db import models


class CommissionPolicy(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='commission_policies')
    name = models.CharField(max_length=150)
    mode = models.CharField(max_length=40)
    window_interval = models.DurationField(blank=True, null=True)
    effective_from = models.DateTimeField(blank=True, null=True)
    effective_to = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'commission_policies'

    def __str__(self):
        return f"{self.name} ({self.mode})"


class BonusRule(models.Model):
    RULE_DIMENSION_CHOICES = [
        ('LEAD_TIME', 'Lead Time'),
        ('SELL_TIME', 'Sell Time'),
        ('USER_REG_TIME', 'User Registration Time'),
        ('SELL_AMOUNT', 'Sell Amount'),
        ('POTENTIAL_PRODUCT', 'Potential Product'),
        ('LEAD_TO_SELL_DELTA', 'Lead to Sell Delta'),
    ]

    OPERATOR_CHOICES = [
        ('EQ', 'Equal'),
        ('NEQ', 'Not Equal'),
        ('GT', 'Greater Than'),
        ('GTE', 'Greater Than or Equal'),
        ('LT', 'Less Than'),
        ('LTE', 'Less Than or Equal'),
        ('BETWEEN', 'Between'),
        ('IN', 'In'),
        ('NOT_IN', 'Not In'),
    ]

    AMOUNT_TYPE_CHOICES = [
        ('fixed', 'Fixed'),
        ('percent_of_sale', 'Percent of Sale'),
    ]

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='bonus_rules')
    name = models.CharField(max_length=150, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    rule_dimension = models.CharField(max_length=40, choices=RULE_DIMENSION_CHOICES, blank=True, null=True)
    operator = models.CharField(max_length=30, choices=OPERATOR_CHOICES, blank=True, null=True)

    # Range / match values (used depending on dimension + operator)
    ts_from = models.DateTimeField(blank=True, null=True)
    ts_to = models.DateTimeField(blank=True, null=True)
    num_from = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    num_to = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    interval_from = models.DurationField(blank=True, null=True)
    interval_to = models.DurationField(blank=True, null=True)
    text_values = models.TextField(blank=True, null=True)
    text_value = models.TextField(blank=True, null=True)

    # Payout
    amount_type = models.CharField(max_length=30, choices=AMOUNT_TYPE_CHOICES, blank=True, null=True)
    amount_value = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True)
    cap_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)

    effective_from = models.DateTimeField(blank=True, null=True)
    effective_to = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'bonus_rules'

    def __str__(self):
        return f"{self.name or f'Rule #{self.id}'} ({self.rule_dimension})"
