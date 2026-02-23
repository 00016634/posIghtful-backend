from rest_framework import viewsets, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth
from .models import CommissionPolicy, BonusRule
from .serializers import CommissionPolicySerializer, BonusRuleSerializer


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
