from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import LeadPipeline, LeadStage, Lead, LeadApplication, LeadStageHistory
from .serializers import (
    LeadPipelineSerializer, LeadStageSerializer,
    LeadSerializer, LeadApplicationSerializer, LeadStageHistorySerializer,
)


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


class LeadPipelineViewSet(TenantScopedViewSet):
    serializer_class = LeadPipelineSerializer
    filterset_fields = ['product', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        return LeadPipeline.objects.select_related('tenant', 'product').all()


class LeadStageViewSet(TenantScopedViewSet):
    serializer_class = LeadStageSerializer
    filterset_fields = ['pipeline', 'is_terminal', 'is_active']
    search_fields = ['name']
    ordering_fields = ['stage_order', 'name']

    def get_queryset(self):
        return LeadStage.objects.select_related('tenant', 'pipeline').all()


class LeadViewSet(TenantScopedViewSet):
    serializer_class = LeadSerializer
    filterset_fields = ['agent', 'customer', 'interaction_type']
    search_fields = ['customer_name', 'customer_phone']
    ordering_fields = ['created_at', 'server_received_at']

    def get_queryset(self):
        qs = Lead.objects.select_related(
            'tenant', 'agent', 'agent__user', 'customer', 'primary_application'
        ).prefetch_related('applications__product', 'applications__current_stage').all()

        user = self.request.user
        if not user.tenant_id:
            return qs

        qs = qs.filter(tenant=user.tenant)

        from users.models import UserRole
        user_roles = set(
            UserRole.objects.filter(user=user, tenant=user.tenant)
            .values_list('role__code', flat=True)
        )

        # Managers, admins, finance see all leads in tenant
        if user_roles & {'MANAGER', 'ADMIN', 'FINANCE'}:
            return qs

        # Supervisors see their team's leads + own
        if 'SUPERVISOR' in user_roles:
            from tenancy.models import Agent
            supervised_agents = Agent.objects.filter(
                parent__user=user, tenant=user.tenant,
            ).values_list('id', flat=True)
            own_agent = Agent.objects.filter(
                user=user, tenant=user.tenant,
            ).values_list('id', flat=True)
            agent_ids = list(supervised_agents) + list(own_agent)
            return qs.filter(agent_id__in=agent_ids)

        # Agents see only their own leads
        from tenancy.models import Agent
        agent = Agent.objects.filter(user=user, tenant=user.tenant).first()
        if agent:
            return qs.filter(agent=agent)

        return qs.none()

    def perform_create(self, serializer):
        from tenancy.models import Agent
        kwargs = {}
        user = self.request.user
        if user.tenant_id:
            kwargs['tenant'] = user.tenant
        # Auto-assign agent from the logged-in user's agent profile
        if not serializer.validated_data.get('agent'):
            agent = Agent.objects.filter(user=user, tenant=user.tenant).first()
            if agent:
                kwargs['agent'] = agent
        serializer.save(**kwargs)


class LeadApplicationViewSet(TenantScopedViewSet):
    serializer_class = LeadApplicationSerializer
    filterset_fields = ['lead', 'product', 'pipeline', 'current_stage', 'is_primary']
    search_fields = ['app_id']
    ordering_fields = ['created_at', 'status_last_updated_at']

    def get_queryset(self):
        return LeadApplication.objects.select_related(
            'tenant', 'lead', 'product', 'pipeline', 'current_stage'
        ).all()


class LeadStageHistoryViewSet(TenantScopedViewSet):
    serializer_class = LeadStageHistorySerializer
    filterset_fields = ['lead', 'lead_application', 'from_stage', 'to_stage']
    ordering_fields = ['changed_at']
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        return LeadStageHistory.objects.select_related(
            'tenant', 'lead', 'lead_application', 'from_stage', 'to_stage'
        ).all()
