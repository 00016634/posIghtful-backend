from rest_framework import viewsets, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Avg, Count
from .models import KPIAgentDaily
from .serializers import KPIAgentDailySerializer


class TenantScopedViewSet(viewsets.ModelViewSet):
    """Base viewset that filters by the authenticated user's tenant."""
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


class KPIAgentDailyViewSet(TenantScopedViewSet):
    serializer_class = KPIAgentDailySerializer
    filterset_fields = ['agent', 'kpi_date']
    search_fields = ['agent__agent_code']
    ordering_fields = ['kpi_date', 'leads_captured', 'revenue_amount']

    def get_queryset(self):
        return KPIAgentDaily.objects.select_related('tenant', 'agent').all()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """Aggregated KPI summary for dashboard widgets."""
    user = request.user
    qs = KPIAgentDaily.objects.all()
    if user.tenant_id:
        qs = qs.filter(tenant=user.tenant)

    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    agent_id = request.query_params.get('agent')

    if date_from:
        qs = qs.filter(kpi_date__gte=date_from)
    if date_to:
        qs = qs.filter(kpi_date__lte=date_to)
    if agent_id:
        qs = qs.filter(agent_id=agent_id)

    totals = qs.aggregate(
        total_leads_captured=Sum('leads_captured'),
        total_leads_converted=Sum('leads_converted'),
        total_revenue=Sum('revenue_amount'),
        total_bonus=Sum('bonus_amount'),
        total_net_profit=Sum('net_profit'),
        avg_conversion_rate=Avg('conversion_rate'),
        days_count=Count('id'),
    )

    # Per-agent breakdown
    per_agent = (
        qs.values('agent', 'agent__agent_code')
        .annotate(
            leads_captured=Sum('leads_captured'),
            leads_converted=Sum('leads_converted'),
            revenue=Sum('revenue_amount'),
            bonus=Sum('bonus_amount'),
            avg_conversion=Avg('conversion_rate'),
        )
        .order_by('-revenue')
    )

    return Response({
        'totals': totals,
        'per_agent': list(per_agent),
    })
