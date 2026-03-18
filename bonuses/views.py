from rest_framework import viewsets, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth
from .models import CommissionPolicy, BonusRule, BonusLedger
from .serializers import CommissionPolicySerializer, BonusRuleSerializer, BonusLedgerSerializer


class TenantScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.tenant_id:
            return qs.filter(tenant=user.tenant)
        return qs

    def perform_create(self, serializer):
        if self.request.user.tenant_id:
            serializer.save(tenant=self.request.user.tenant)
        else:
            serializer.save()


class CommissionPolicyViewSet(TenantScopedViewSet):
    serializer_class = CommissionPolicySerializer
    filterset_fields = ['mode', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'effective_from', 'created_at']

    def get_queryset(self):
        return CommissionPolicy.objects.select_related('tenant').all()


class BonusRuleViewSet(TenantScopedViewSet):
    serializer_class = BonusRuleSerializer
    filterset_fields = ['rule_dimension', 'operator', 'amount_type', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'effective_from', 'created_at']

    def get_queryset(self):
        return BonusRule.objects.select_related('tenant').all()


class BonusLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BonusLedgerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['agent', 'rule']
    ordering_fields = ['created_at', 'bonus_amount']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = BonusLedger.objects.select_related(
            'agent__user', 'rule', 'sale', 'tenant',
        ).all()
        user = self.request.user
        if user.tenant_id:
            qs = qs.filter(tenant=user.tenant)

        # Optional date range filtering
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_bonuses_view(request):
    """Group KPIAgentDaily by month, sum bonus_amount, count agents."""
    from analytics.models import KPIAgentDaily

    qs = KPIAgentDaily.objects.all()
    if request.user.tenant_id:
        qs = qs.filter(tenant=request.user.tenant)

    monthly = qs.annotate(
        month=TruncMonth('kpi_date')
    ).values('month').annotate(
        totalBonus=Sum('bonus_amount'),
        agentCount=Count('agent', distinct=True),
    ).order_by('-month')[:12]

    result = []
    for row in monthly:
        total = float(row['totalBonus'] or 0)
        count = row['agentCount'] or 1
        result.append({
            'month': row['month'].strftime('%b %Y'),
            'totalBonus': total,
            'agentCount': count,
            'avgPerAgent': round(total / max(count, 1)),
        })

    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_bonus_detail_view(request, month):
    """Per-agent breakdown for a given month (format: YYYY-MM)."""
    from analytics.models import KPIAgentDaily
    import datetime

    try:
        year, mon = month.split('-')
        start_date = datetime.date(int(year), int(mon), 1)
        if int(mon) == 12:
            end_date = datetime.date(int(year) + 1, 1, 1)
        else:
            end_date = datetime.date(int(year), int(mon) + 1, 1)
    except (ValueError, IndexError):
        return Response({'error': 'Invalid month format. Use YYYY-MM'}, status=400)

    qs = KPIAgentDaily.objects.filter(
        kpi_date__gte=start_date,
        kpi_date__lt=end_date,
    )
    if request.user.tenant_id:
        qs = qs.filter(tenant=request.user.tenant)

    per_agent = qs.values(
        'agent__agent_code', 'agent__user__full_name'
    ).annotate(
        conversions=Sum('leads_converted'),
        totalSales=Sum('revenue_amount'),
        bonusAmount=Sum('bonus_amount'),
    ).order_by('-totalSales')

    result = []
    for row in per_agent:
        result.append({
            'agentName': row['agent__user__full_name'] or 'Unknown',
            'agentCode': row['agent__agent_code'] or '',
            'conversions': row['conversions'] or 0,
            'totalSales': float(row['totalSales'] or 0),
            'bonusAmount': float(row['bonusAmount'] or 0),
        })

    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_audit_view(request, month):
    """Per-sale audit trail for a given month (format: YYYY-MM).
    Returns each completed sale with lead, customer, bonus rule applied."""
    from conversions.models import Sale
    import datetime

    try:
        year, mon = month.split('-')
        start_date = datetime.date(int(year), int(mon), 1)
        if int(mon) == 12:
            end_date = datetime.date(int(year) + 1, 1, 1)
        else:
            end_date = datetime.date(int(year), int(mon) + 1, 1)
    except (ValueError, IndexError):
        return Response({'error': 'Invalid month format. Use YYYY-MM'}, status=400)

    sales = Sale.objects.filter(
        sold_at__date__gte=start_date,
        sold_at__date__lt=end_date,
        status='completed',
    ).select_related(
        'agent__user', 'customer', 'product', 'lead'
    ).order_by('-sold_at')

    if request.user.tenant_id:
        sales = sales.filter(tenant=request.user.tenant)

    # Build a map of sale_id -> BonusLedger for pre-recorded bonuses
    ledger_map = {}
    ledger_entries = BonusLedger.objects.filter(
        sale__in=sales
    ).select_related('rule')
    for entry in ledger_entries:
        ledger_map[entry.sale_id] = entry

    # Fallback: load active bonus rules for sales without ledger entries
    rules = None

    result = []
    for sale in sales:
        amount = float(sale.amount)
        ledger = ledger_map.get(sale.id)

        if ledger:
            # Use pre-recorded bonus from BonusLedger
            result.append({
                'id': sale.id,
                'agentName': sale.agent.user.full_name if sale.agent and sale.agent.user else 'Unknown',
                'agentCode': sale.agent.agent_code if sale.agent else '',
                'leadId': f'LEAD-{sale.lead_id}' if sale.lead_id else '-',
                'customerName': sale.customer.full_name if sale.customer else '-',
                'productName': sale.product.name if sale.product else '-',
                'saleAmount': amount,
                'saleDate': sale.sold_at.strftime('%Y-%m-%d'),
                'ruleName': ledger.rule.name if ledger.rule else 'Default (10%)',
                'ruleType': (f'{ledger.rule.get_amount_type_display()} – {ledger.rule.get_rule_dimension_display()}'
                             if ledger.rule else 'Percent of sale'),
                'bonusAmount': float(ledger.bonus_amount),
                'calculation': ledger.calculation_detail,
            })
        else:
            # Fallback: calculate on the fly for historical sales without ledger
            if rules is None:
                rules = list(BonusRule.objects.filter(
                    is_active=True,
                    effective_from__lte=end_date,
                ))
                if request.user.tenant_id:
                    rules = [r for r in rules if r.tenant_id == request.user.tenant_id]

            applied_rule = None
            bonus = 0.0
            for rule in rules:
                matches = False
                if rule.rule_dimension == 'SELL_AMOUNT':
                    threshold = float(rule.num_from or 0)
                    if rule.operator == 'GTE' and amount >= threshold:
                        matches = True
                    elif rule.operator == 'GT' and amount > threshold:
                        matches = True
                elif rule.rule_dimension == 'POTENTIAL_PRODUCT' and sale.product:
                    product_codes = [c.strip() for c in (rule.text_values or '').split(',')]
                    if sale.product.code in product_codes:
                        matches = True

                if matches:
                    if rule.amount_type == 'percent_of_sale':
                        bonus = amount * float(rule.amount_value) / 100
                        cap = float(rule.cap_amount or 0)
                        if cap > 0:
                            bonus = min(bonus, cap)
                    else:
                        bonus = float(rule.amount_value)
                    applied_rule = rule
                    break

            if not applied_rule:
                bonus = round(amount * 0.10, 2)

            result.append({
                'id': sale.id,
                'agentName': sale.agent.user.full_name if sale.agent and sale.agent.user else 'Unknown',
                'agentCode': sale.agent.agent_code if sale.agent else '',
                'leadId': f'LEAD-{sale.lead_id}' if sale.lead_id else '-',
                'customerName': sale.customer.full_name if sale.customer else '-',
                'productName': sale.product.name if sale.product else '-',
                'saleAmount': amount,
                'saleDate': sale.sold_at.strftime('%Y-%m-%d'),
                'ruleName': applied_rule.name if applied_rule else 'Default (10%)',
                'ruleType': (f'{applied_rule.get_amount_type_display()} – {applied_rule.get_rule_dimension_display()}'
                             if applied_rule else 'Percent of sale'),
                'bonusAmount': round(bonus, 2),
                'calculation': (f'{float(applied_rule.amount_value)}% of ${amount:,.0f}'
                               if applied_rule and applied_rule.amount_type == 'percent_of_sale'
                               else f'${float(applied_rule.amount_value):,.0f} fixed'
                               if applied_rule else f'10% of ${amount:,.0f}'),
            })

    return Response(result)
