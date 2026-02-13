from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Sale
from .serializers import SaleSerializer


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


class SaleViewSet(TenantScopedViewSet):
    serializer_class = SaleSerializer
    filterset_fields = ['agent', 'product', 'customer', 'status']
    search_fields = ['customer__full_name', 'agent__agent_code']
    ordering_fields = ['sold_at', 'amount', 'created_at']

    def get_queryset(self):
        return Sale.objects.select_related(
            'tenant', 'lead', 'lead_application',
            'customer', 'agent', 'product'
        ).all()
