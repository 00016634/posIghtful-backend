from rest_framework import viewsets, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta

from .models import Tenant, Region, City, Product, Customer, Agent, SubscriptionPlan, Subscription, Payment
from .serializers import (
    TenantSerializer, RegionSerializer, CitySerializer,
    ProductSerializer, CustomerSerializer, AgentSerializer,
    SubscriptionPlanSerializer, OnboardingSerializer,
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


@api_view(['GET'])
@permission_classes([AllowAny])
def plan_list_view(request):
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    serializer = SubscriptionPlanSerializer(plans, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def onboarding_view(request):
    serializer = OnboardingSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    plan = SubscriptionPlan.objects.get(id=data['plan_id'])
    card_digits = data['card_number']

    with transaction.atomic():
        # 1. Create Tenant
        base_code = slugify(data['company_name'])[:60]
        code = base_code
        counter = 1
        while Tenant.objects.filter(code=code).exists():
            code = f"{base_code}-{counter}"
            counter += 1

        tenant = Tenant.objects.create(
            name=data['company_name'],
            code=code,
        )

        # 2. Create Admin User
        from users.models import User, Role, UserRole
        username = data['admin_email'].split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=data['admin_email'],
            full_name=data['admin_full_name'],
            password=data['admin_password'],
            tenant=tenant,
        )

        # 3. Assign ADMIN role
        admin_role = Role.objects.get(code='ADMIN')
        UserRole.objects.create(tenant=tenant, user=user, role=admin_role)

        # 4. Create Subscription (14-day trial)
        now = timezone.now()
        subscription = Subscription.objects.create(
            tenant=tenant,
            plan=plan,
            status='trial',
            trial_end=now + timedelta(days=14),
            current_period_start=now,
            current_period_end=now + timedelta(days=14),
        )

        # 5. Create Payment record (first4 + last4 only)
        Payment.objects.create(
            tenant=tenant,
            subscription=subscription,
            card_first4=card_digits[:4],
            card_last4=card_digits[-4:],
            cardholder_name=data['cardholder_name'],
            billing_email=data['billing_email'],
            amount=plan.price,
            currency='USD',
            status='completed',
        )

    # 6. Return JWT tokens (auto-login)
    from users.serializers import UserSerializer
    refresh = RefreshToken.for_user(user)
    user_data = UserSerializer(user).data

    return Response({
        'user': user_data,
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'message': 'Organization created successfully',
    }, status=status.HTTP_201_CREATED)
