from django.db import models


class Tenant(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'tenants'

    def __str__(self):
        return f"{self.name} ({self.code})"


class Region(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='regions')
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'regions'

    def __str__(self):
        return f"{self.name} ({self.tenant.code})"


class City(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='cities')
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='cities')
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'cities'

    def __str__(self):
        return f"{self.name} ({self.region.name})"


class Product(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='products')
    code = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=120, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'products'

    def __str__(self):
        return f"{self.name} ({self.code or 'No Code'})"


class Customer(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='customers')
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_profile')
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'customers'
        indexes = [
            models.Index(fields=['tenant', 'phone']),
        ]

    def __str__(self):
        return f"{self.full_name or 'Unnamed'} ({self.phone or 'No Phone'})"


class Agent(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='agents')
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='agent_profile')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')
    agent_code = models.CharField(max_length=100, blank=True, null=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='agents')
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='agents')
    hired_at = models.DateField(blank=True, null=True)
    terminated_at = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=30, default='active')
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'agents'
        unique_together = [['tenant', 'agent_code']]

    def __str__(self):
        return f"{self.agent_code or f'Agent #{self.id}'} - {self.tenant.code}"


class SubscriptionPlan(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, default='')
    max_agents = models.IntegerField(default=5)
    storage_limit = models.CharField(max_length=50, default='1 GB')
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscription_plans'

    def __str__(self):
        return f"{self.name} (${self.price}/mo)"


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.BigAutoField(primary_key=True)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    trial_end = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscriptions'

    def __str__(self):
        return f"{self.tenant.name} – {self.plan.name} ({self.status})"


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    card_brand = models.CharField(max_length=20, blank=True, default='')
    card_first4 = models.CharField(max_length=4, blank=True, default='')
    card_last4 = models.CharField(max_length=4, blank=True, default='')
    cardholder_name = models.CharField(max_length=255, blank=True, default='')
    billing_email = models.EmailField(blank=True, default='')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'

    def __str__(self):
        return f"Payment #{self.id} – {self.tenant.name} – ${self.amount} ({self.status})"
