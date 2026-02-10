from django.contrib import admin
from .models import CommissionPolicy, BonusRule


@admin.register(CommissionPolicy)
class CommissionPolicyAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'mode', 'is_active', 'effective_from', 'effective_to', 'tenant']
    list_filter = ['is_active', 'tenant', 'mode']
    search_fields = ['name']


@admin.register(BonusRule)
class BonusRuleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'rule_dimension', 'operator', 'amount_type', 'amount_value', 'is_active']
    list_filter = ['is_active', 'tenant', 'rule_dimension', 'amount_type']
    search_fields = ['name']
