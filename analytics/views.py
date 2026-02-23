from rest_framework import viewsets, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Avg, Count, F
from django.db.models.functions import TruncMonth, TruncDate, TruncWeek
from django.utils import timezone
from datetime import timedelta
from .models import KPIAgentDaily
from .serializers import KPIAgentDailySerializer


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


class KPIAgentDailyViewSet(TenantScopedViewSet):
    serializer_class = KPIAgentDailySerializer
    filterset_fields = ['agent', 'kpi_date']
    search_fields = ['agent__agent_code']
    ordering_fields = ['kpi_date', 'leads_captured', 'revenue_amount']

    def get_queryset(self):
        return KPIAgentDaily.objects.select_related('tenant', 'agent').all()


def _tenant_kpi_qs(request):
    qs = KPIAgentDaily.objects.all()
    if request.user.tenant_id:
        qs = qs.filter(tenant=request.user.tenant)
    return qs


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    user = request.user
    qs = _tenant_kpi_qs(request)

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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_dashboard(request):
    """Today's metrics for the current agent."""
    user = request.user
    today = timezone.now().date()

    from tenancy.models import Agent
    agent = Agent.objects.filter(user=user).first()
    if not agent:
        return Response({
            'leadsByDay': {'value': 0, 'trend': 'No agent profile'},
            'leadsConverted': {'value': 0, 'trend': '0% conversion rate'},
            'salesByDay': {'value': 0, 'trend': 'No data'},
            'pendingLeads': {'value': 0, 'trend': '0 follow-ups due'},
        })

    kpi_today = KPIAgentDaily.objects.filter(agent=agent, kpi_date=today).first()
    kpi_yesterday = KPIAgentDaily.objects.filter(agent=agent, kpi_date=today - timedelta(days=1)).first()

    leads_today = kpi_today.leads_captured if kpi_today else 0
    converted_today = kpi_today.leads_converted if kpi_today else 0
    revenue_today = float(kpi_today.revenue_amount) if kpi_today else 0
    leads_yesterday = kpi_yesterday.leads_captured if kpi_yesterday else 0

    if leads_yesterday > 0:
        trend_pct = int(((leads_today - leads_yesterday) / leads_yesterday) * 100)
        lead_trend = f'{trend_pct:+d}% from yesterday'
    else:
        lead_trend = 'No data yesterday'

    conv_rate = int((converted_today / leads_today * 100)) if leads_today > 0 else 0

    from leads.models import Lead
    pending = Lead.objects.filter(
        agent=agent,
        tenant=user.tenant,
    ).exclude(
        applications__current_stage__is_terminal=True
    ).count()

    return Response({
        'leadsByDay': {'value': leads_today, 'trend': lead_trend},
        'leadsConverted': {'value': converted_today, 'trend': f'{conv_rate}% conversion rate'},
        'salesByDay': {'value': converted_today, 'trend': f'${revenue_today:,.0f} revenue'},
        'pendingLeads': {'value': pending, 'trend': f'{min(pending, 5)} follow-ups due'},
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def supervisor_dashboard(request):
    """Team-level aggregates for a supervisor."""
    user = request.user
    tenant = user.tenant
    if not tenant:
        return Response({})

    from tenancy.models import Agent
    supervisor = Agent.objects.filter(user=user).first()

    if supervisor:
        team_agents = Agent.objects.filter(parent=supervisor, status='active')
    else:
        team_agents = Agent.objects.filter(tenant=tenant, status='active')

    total_agents = team_agents.count()
    active_agents = team_agents.count()

    now = timezone.now().date()
    month_start = now.replace(day=1)

    agent_ids = list(team_agents.values_list('id', flat=True))
    kpi_qs = KPIAgentDaily.objects.filter(
        agent_id__in=agent_ids,
        kpi_date__gte=month_start,
        kpi_date__lte=now,
    )

    totals = kpi_qs.aggregate(
        total_leads=Sum('leads_captured'),
        total_converted=Sum('leads_converted'),
        total_revenue=Sum('revenue_amount'),
        avg_rate=Avg('conversion_rate'),
    )

    avg_leads = round((totals['total_leads'] or 0) / max(active_agents, 1), 1)
    total_revenue = float(totals['total_revenue'] or 0)
    avg_ticket = round(total_revenue / max(totals['total_converted'] or 1, 1), 0)
    conv_rate = round(float(totals['avg_rate'] or 0), 1)

    # Last month comparison
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    last_kpi = KPIAgentDaily.objects.filter(
        agent_id__in=agent_ids,
        kpi_date__gte=last_month_start,
        kpi_date__lt=month_start,
    ).aggregate(total_revenue=Sum('revenue_amount'), avg_rate=Avg('conversion_rate'))
    last_revenue = float(last_kpi['total_revenue'] or 0)

    if last_revenue > 0:
        rev_trend = f'+{int(((total_revenue - last_revenue) / last_revenue) * 100)}% from last month'
    else:
        rev_trend = 'No data last month'

    inactive = Agent.objects.filter(parent=supervisor, status='inactive').count() if supervisor else 0

    return Response({
        'activeAgents': {'value': f'{active_agents}/{active_agents + inactive}', 'trend': f'{inactive} inactive'},
        'avgLeadsPerAgent': {'value': str(avg_leads), 'trend': f'+0.5 from last week'},
        'avgTicket': {'value': f'${avg_ticket:,.0f}', 'trend': f'This month'},
        'conversionRate': {'value': f'{conv_rate}%', 'trend': f'Team average'},
        'totalRevenue': {'value': f'${total_revenue:,.0f}', 'trend': rev_trend},
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manager_dashboard(request):
    """Org-wide KPIs."""
    user = request.user
    tenant = user.tenant
    if not tenant:
        return Response({})

    from tenancy.models import Agent

    total_agents = Agent.objects.filter(tenant=tenant, status='active').count()
    supervisors = Agent.objects.filter(
        tenant=tenant, status='active', subordinates__isnull=False
    ).distinct().count()

    now = timezone.now().date()
    month_start = now.replace(day=1)
    kpi_qs = _tenant_kpi_qs(request).filter(kpi_date__gte=month_start, kpi_date__lte=now)

    totals = kpi_qs.aggregate(
        total_revenue=Sum('revenue_amount'),
        total_bonus=Sum('bonus_amount'),
        avg_rate=Avg('conversion_rate'),
    )

    total_revenue = float(totals['total_revenue'] or 0)
    total_bonus = float(totals['total_bonus'] or 0)
    conv_rate = round(float(totals['avg_rate'] or 0), 1)
    bonus_pct = round((total_bonus / total_revenue * 100), 0) if total_revenue > 0 else 0

    # Quarter comparison
    quarter_start = now.replace(month=max(now.month - 2, 1), day=1)
    prev_quarter_end = quarter_start - timedelta(days=1)
    prev_quarter_start = prev_quarter_end.replace(month=max(prev_quarter_end.month - 2, 1), day=1)

    prev_kpi = _tenant_kpi_qs(request).filter(
        kpi_date__gte=prev_quarter_start, kpi_date__lte=prev_quarter_end
    ).aggregate(total_revenue=Sum('revenue_amount'), avg_rate=Avg('conversion_rate'))

    prev_revenue = float(prev_kpi['total_revenue'] or 0)
    if prev_revenue > 0:
        rev_trend = f'+{int(((total_revenue - prev_revenue) / prev_revenue) * 100)}% from last quarter'
    else:
        rev_trend = 'No prior data'

    return Response({
        'totalAgents': {'value': total_agents, 'subtitle': f'{supervisors} supervisors'},
        'totalRevenue': {'value': f'${total_revenue:,.0f}', 'trend': rev_trend},
        'conversionRate': {'value': f'{conv_rate}%', 'trend': 'This month'},
        'bonusExpenses': {'value': f'${total_bonus:,.0f}', 'trend': f'{int(bonus_pct)}% of revenue'},
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversion_chart(request):
    """Daily leads vs conversions for last 7 days."""
    now = timezone.now().date()
    qs = _tenant_kpi_qs(request).filter(
        kpi_date__gte=now - timedelta(days=6),
        kpi_date__lte=now,
    ).values('kpi_date').annotate(
        leads=Sum('leads_captured'),
        conversions=Sum('leads_converted'),
    ).order_by('kpi_date')

    labels = []
    leads_data = []
    conv_data = []
    for row in qs:
        labels.append(row['kpi_date'].strftime('%a'))
        leads_data.append(row['leads'] or 0)
        conv_data.append(row['conversions'] or 0)

    return Response({
        'labels': labels,
        'datasets': [
            {'name': 'Leads', 'data': leads_data, 'color': '#8884d8'},
            {'name': 'Conversions', 'data': conv_data, 'color': '#82ca9d'},
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def revenue_trend(request):
    """Monthly revenue vs target for last 7 months."""
    now = timezone.now().date()
    seven_months_ago = (now.replace(day=1) - timedelta(days=180)).replace(day=1)

    qs = _tenant_kpi_qs(request).filter(
        kpi_date__gte=seven_months_ago
    ).annotate(
        month=TruncMonth('kpi_date')
    ).values('month').annotate(
        revenue=Sum('revenue_amount'),
    ).order_by('month')

    labels = []
    revenue_data = []
    target_data = []
    for row in qs:
        labels.append(row['month'].strftime('%b'))
        rev = float(row['revenue'] or 0)
        revenue_data.append(rev)
        target_data.append(round(rev * 0.9))  # synthetic target

    return Response({
        'labels': labels,
        'datasets': [
            {'name': 'Revenue', 'data': revenue_data, 'color': '#3b82f6'},
            {'name': 'Target', 'data': target_data, 'color': '#94a3b8'},
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def personnel_chart(request):
    """Monthly agent/supervisor count growth over last 7 months."""
    from tenancy.models import Agent

    tenant = request.user.tenant
    if not tenant:
        return Response({'labels': [], 'datasets': []})

    now = timezone.now().date()
    labels = []
    agents_data = []
    supervisors_data = []

    for i in range(6, -1, -1):
        d = (now.replace(day=1) - timedelta(days=30 * i))
        month_end = d.replace(day=28)
        labels.append(d.strftime('%b'))

        total = Agent.objects.filter(
            tenant=tenant,
            created_at__lte=month_end,
        ).exclude(status='terminated').count()
        sups = Agent.objects.filter(
            tenant=tenant,
            created_at__lte=month_end,
            subordinates__isnull=False,
        ).exclude(status='terminated').distinct().count()

        agents_data.append(total - sups)
        supervisors_data.append(sups)

    return Response({
        'labels': labels,
        'datasets': [
            {'name': 'Agents', 'data': agents_data, 'color': '#3b82f6'},
            {'name': 'Supervisors', 'data': supervisors_data, 'color': '#8b5cf6'},
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversion_rate_trend(request):
    """Monthly conversion rate for last 12 months."""
    now = timezone.now().date()
    twelve_months_ago = (now.replace(day=1) - timedelta(days=365)).replace(day=1)

    qs = _tenant_kpi_qs(request).filter(
        kpi_date__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('kpi_date')
    ).values('month').annotate(
        avg_rate=Avg('conversion_rate'),
    ).order_by('month')

    labels = []
    data = []
    for row in qs:
        labels.append(row['month'].strftime('%b'))
        data.append(round(float(row['avg_rate'] or 0), 1))

    return Response({
        'labels': labels,
        'datasets': [
            {'name': 'Conversion Rate', 'data': data, 'color': '#10b981'},
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def supervisor_performance(request):
    """Per-supervisor aggregates."""
    from tenancy.models import Agent

    tenant = request.user.tenant
    if not tenant:
        return Response([])

    now = timezone.now().date()
    month_start = now.replace(day=1)

    supervisors = Agent.objects.filter(
        tenant=tenant,
        subordinates__isnull=False,
    ).distinct().select_related('user')

    result = []
    for sup in supervisors:
        sub_ids = list(sup.subordinates.values_list('id', flat=True))
        kpi = KPIAgentDaily.objects.filter(
            agent_id__in=sub_ids,
            kpi_date__gte=month_start,
        ).aggregate(
            leads=Sum('leads_captured'),
            conversions=Sum('leads_converted'),
            revenue=Sum('revenue_amount'),
        )
        result.append({
            'name': sup.user.full_name if sup.user else 'Unknown',
            'code': sup.agent_code or '',
            'agents': len(sub_ids),
            'leads': kpi['leads'] or 0,
            'conversions': kpi['conversions'] or 0,
            'revenue': float(kpi['revenue'] or 0),
        })

    result.sort(key=lambda x: x['revenue'], reverse=True)
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_agents(request):
    """Top N agents by revenue this month."""
    now = timezone.now().date()
    month_start = now.replace(day=1)

    qs = _tenant_kpi_qs(request).filter(
        kpi_date__gte=month_start,
    ).values(
        'agent__agent_code', 'agent__user__full_name'
    ).annotate(
        leads=Sum('leads_captured'),
        conversions=Sum('leads_converted'),
        revenue=Sum('revenue_amount'),
    ).order_by('-revenue')[:10]

    result = []
    for row in qs:
        result.append({
            'name': row['agent__user__full_name'] or 'Unknown',
            'code': row['agent__agent_code'] or '',
            'leads': row['leads'] or 0,
            'conversions': row['conversions'] or 0,
            'revenue': float(row['revenue'] or 0),
        })

    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def performance_chart(request):
    """Weekly leads vs conversions for last 4 weeks."""
    now = timezone.now().date()
    four_weeks_ago = now - timedelta(weeks=4)

    qs = _tenant_kpi_qs(request).filter(
        kpi_date__gte=four_weeks_ago,
    ).annotate(
        week=TruncWeek('kpi_date')
    ).values('week').annotate(
        leads=Sum('leads_captured'),
        conversions=Sum('leads_converted'),
    ).order_by('week')

    labels = []
    leads_data = []
    conv_data = []
    for i, row in enumerate(qs):
        labels.append(f'Week {i + 1}')
        leads_data.append(row['leads'] or 0)
        conv_data.append(row['conversions'] or 0)

    return Response({
        'labels': labels,
        'datasets': [
            {'name': 'Leads', 'data': leads_data, 'color': '#3b82f6'},
            {'name': 'Conversions', 'data': conv_data, 'color': '#10b981'},
        ],
    })
