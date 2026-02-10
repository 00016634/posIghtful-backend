from django.contrib import admin
from .models import KPIAgentDaily


@admin.register(KPIAgentDaily)
class KPIAgentDailyAdmin(admin.ModelAdmin):
    list_display = ['id', 'agent', 'kpi_date', 'leads_captured', 'leads_converted', 'conversion_rate', 'revenue_amount', 'bonus_amount', 'net_profit']
    list_filter = ['tenant', 'kpi_date']
    search_fields = ['agent__agent_code']
