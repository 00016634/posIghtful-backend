from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Tenant, Region, City, Product, Customer, Agent
from .serializers import (
    TenantSerializer, RegionSerializer, CitySerializer,
    ProductSerializer, CustomerSerializer, AgentSerializer,
)


class TenantViewSet(viewsets.ModelViewSet):
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        return Tenant.objects.all()


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


class RegionViewSet(TenantScopedViewSet):
    serializer_class = RegionSerializer
    filterset_fields = ['is_active']
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        return Region.objects.select_related('tenant').all()


class CityViewSet(TenantScopedViewSet):
    serializer_class = CitySerializer
    filterset_fields = ['region', 'is_active']
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        return City.objects.select_related('tenant', 'region').all()


class ProductViewSet(TenantScopedViewSet):
    serializer_class = ProductSerializer
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'code', 'category']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        return Product.objects.select_related('tenant').all()


class CustomerViewSet(TenantScopedViewSet):
    serializer_class = CustomerSerializer
    filterset_fields = ['user']
    search_fields = ['full_name', 'phone']
    ordering_fields = ['full_name', 'created_at']

    def get_queryset(self):
        return Customer.objects.select_related('tenant', 'user').all()


class AgentViewSet(TenantScopedViewSet):
    serializer_class = AgentSerializer
    filterset_fields = ['region', 'city', 'status', 'parent']
    search_fields = ['agent_code', 'user__full_name']
    ordering_fields = ['agent_code', 'hired_at', 'created_at']

    def get_queryset(self):
        return Agent.objects.select_related(
            'tenant', 'user', 'parent', 'region', 'city'
        ).all()
