from django.db import models


class Tenant(models.Model):
    """Multi-tenant organization model"""
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=80, unique=True)  # e.g., "tbc_uz", "pilot_1"
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenants'

    def __str__(self):
        return f"{self.name} ({self.code})"


class Region(models.Model):
    """Geographic regions within a tenant"""
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='regions')
    name = models.CharField(max_length=150)  # e.g., "Tashkent", "Samarkand"
    code = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'regions'

    def __str__(self):
        return f"{self.name} ({self.tenant.code})"


class Outlet(models.Model):
    """Sales outlets/stores within a tenant"""
    STORE = 'store'
    CAMPUS = 'campus'
    POPUP = 'pop-up'
    PARTNER = 'partner'

    OUTLET_TYPE_CHOICES = [
        (STORE, 'Store'),
        (CAMPUS, 'Campus'),
        (POPUP, 'Pop-up'),
        (PARTNER, 'Partner'),
    ]

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='outlets')
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, related_name='outlets')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=80, blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    outlet_type = models.CharField(max_length=100, choices=OUTLET_TYPE_CHOICES, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'outlets'

    def __str__(self):
        return f"{self.name} ({self.code or 'No Code'})"


class Agent(models.Model):
    """Sales agents working at outlets"""
    ACTIVE = 'active'
    ON_LEAVE = 'on_leave'
    DISABLED = 'disabled'

    STATUS_CHOICES = [
        (ACTIVE, 'Active'),
        (ON_LEAVE, 'On Leave'),
        (DISABLED, 'Disabled'),
    ]

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='agents')
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='agent_profile')
    outlet = models.ForeignKey(Outlet, on_delete=models.SET_NULL, null=True, blank=True, related_name='agents')
    agent_code = models.CharField(max_length=100, blank=True, null=True)  # human-readable code
    hired_at = models.DateField(blank=True, null=True)
    terminated_at = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'agents'

    def __str__(self):
        return f"{self.agent_code or f'Agent #{self.id}'} - {self.tenant.code}"
