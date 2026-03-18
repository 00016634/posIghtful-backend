from django.contrib import admin
from .models import CommissionPolicy, BonusRule, BonusLedger


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


@admin.register(BonusLedger)
class BonusLedgerAdmin(admin.ModelAdmin):
    list_display = ['id', 'sale', 'agent', 'rule', 'bonus_amount', 'created_at']
    list_filter = ['tenant', 'rule']
    search_fields = ['agent__agent_code', 'agent__user__full_name']
    raw_id_fields = ['sale', 'agent', 'rule']
