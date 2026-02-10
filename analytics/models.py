from django.db import models


class KPIAgentDaily(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.CASCADE, related_name='agent_kpis')
    agent = models.ForeignKey('tenancy.Agent', on_delete=models.CASCADE, related_name='daily_kpis')
    kpi_date = models.DateField()
    leads_captured = models.IntegerField(default=0)
    leads_converted = models.IntegerField(default=0)
    conversion_rate = models.DecimalField(max_digits=8, decimal_places=4, blank=True, null=True)
    revenue_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    bonus_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    avg_time_to_convert = models.DurationField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        db_table = 'kpi_agent_daily'
        unique_together = [['tenant', 'agent', 'kpi_date']]
        indexes = [
            models.Index(fields=['tenant', 'kpi_date']),
            models.Index(fields=['agent', 'kpi_date']),
        ]

    def __str__(self):
        return f"Agent {self.agent_id} – {self.kpi_date} – {self.leads_captured} leads"
