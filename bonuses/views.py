from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import CommissionPolicy, BonusRule
from .serializers import CommissionPolicySerializer, BonusRuleSerializer


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
