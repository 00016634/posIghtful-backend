from django.db import models


class Sale(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='sales')

    lead = models.ForeignKey('leads.Lead', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    lead_application = models.ForeignKey('leads.LeadApplication', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')

    customer = models.ForeignKey('tenancy.Customer', on_delete=models.CASCADE, related_name='sales')
    agent = models.ForeignKey('tenancy.Agent', on_delete=models.CASCADE, related_name='sales')
    product = models.ForeignKey('tenancy.Product', on_delete=models.CASCADE, related_name='sales')

    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=30)
    sold_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = 'sales'

    def __str__(self):
        return f"Sale {self.id} – {self.amount} ({self.status})"
