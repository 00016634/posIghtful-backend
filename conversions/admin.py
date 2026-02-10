from django.contrib import admin
from .models import Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'agent', 'product', 'amount', 'status', 'sold_at']
    list_filter = ['status', 'tenant', 'product']
    search_fields = ['customer__full_name', 'agent__agent_code']
