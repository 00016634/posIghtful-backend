from rest_framework import status, viewsets, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import update_session_auth_hash
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    RoleSerializer,
    UserManagementSerializer,
)
from .models import User, Role, UserRole


@swagger_auto_schema(
    method='post',
    request_body=RegisterSerializer,
    responses={
        201: openapi.Response('User registered successfully', UserSerializer),
        400: 'Bad Request'
    },
    operation_description="Register a new user account"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        user_data = UserSerializer(user).data
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': user_data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    request_body=LoginSerializer,
    responses={200: 'Login successful', 400: 'Bad Request'},
    operation_description="Login with username and password"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        user_data = UserSerializer(user).data
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': user_data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    responses={200: 'Logout successful', 400: 'Bad Request'},
    operation_description="Logout user (blacklist refresh token)"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=ChangePasswordSerializer,
    responses={200: 'Password changed successfully', 400: 'Bad Request'},
    operation_description="Change user password"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'error': 'Old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        update_session_auth_hash(request, user)
        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def role_list_view(request):
    roles = Role.objects.all().order_by('id')
    serializer = RoleSerializer(roles, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ─── User Management ViewSet ────────────────────────────────────

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserManagementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['username', 'full_name', 'email', 'phone_number']
    ordering_fields = ['full_name', 'created_at']

    def get_queryset(self):
        qs = User.objects.prefetch_related('user_roles__role').all()
        user = self.request.user
        if user.tenant_id:
            qs = qs.filter(tenant=user.tenant)
        return qs

    def perform_create(self, serializer):
        password = self.request.data.get('password', 'DefaultPass123!')
        user = serializer.save(tenant=self.request.user.tenant)
        user.set_password(password)
        user.save()
        # Assign role if provided
        role_code = self.request.data.get('role')
        if role_code and self.request.user.tenant:
            try:
                role = Role.objects.get(code=role_code.upper())
                UserRole.objects.get_or_create(
                    tenant=self.request.user.tenant, user=user, role=role
                )
            except Role.DoesNotExist:
                pass

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_stats_view(request):
    user = request.user
    tenant = user.tenant
    if not tenant:
        return Response({'error': 'No tenant'}, status=status.HTTP_400_BAD_REQUEST)

    from tenancy.models import Product, Agent
    total_users = User.objects.filter(tenant=tenant).count()
    active_users = User.objects.filter(tenant=tenant, is_active=True).count()
    total_products = Product.objects.filter(tenant=tenant).count()

    return Response({
        'tenantName': tenant.name,
        'totalUsers': total_users,
        'activeUsers': active_users,
        'totalProducts': total_products,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_activity_view(request):
    user = request.user
    tenant = user.tenant
    if not tenant:
        return Response([])

    from tenancy.models import Product, Agent
    from django.utils import timezone
    import datetime

    activities = []

    # Recent users
    recent_users = User.objects.filter(
        tenant=tenant
    ).order_by('-created_at')[:5]
    for u in recent_users:
        roles = [ur.role.name for ur in u.user_roles.select_related('role').all()]
        role_str = roles[0] if roles else 'User'
        delta = timezone.now() - u.created_at
        activities.append({
            'action': 'New user created',
            'detail': f'{u.full_name or u.username} ({role_str})',
            'time': _humanize_delta(delta),
            'timestamp': u.created_at.isoformat(),
        })

    # Recent products
    recent_products = Product.objects.filter(
        tenant=tenant
    ).order_by('-created_at')[:5]
    for p in recent_products:
        delta = timezone.now() - p.created_at
        activities.append({
            'action': 'New product added',
            'detail': p.name,
            'time': _humanize_delta(delta),
            'timestamp': p.created_at.isoformat(),
        })

    activities.sort(key=lambda a: a['timestamp'], reverse=True)
    return Response(activities[:10])


def _humanize_delta(delta):
    seconds = int(delta.total_seconds())
    if seconds < 3600:
        mins = seconds // 60
        return f'{mins} minute{"s" if mins != 1 else ""} ago'
    elif seconds < 86400:
        hours = seconds // 3600
        return f'{hours} hour{"s" if hours != 1 else ""} ago'
    else:
        days = seconds // 86400
        return f'{days} day{"s" if days != 1 else ""} ago'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def accountant_data_view(request):
    user = request.user
    tenant = user.tenant
    if not tenant:
        return Response({'error': 'No tenant'}, status=status.HTTP_400_BAD_REQUEST)

    from analytics.models import KPIAgentDaily
    from conversions.models import Sale
    from tenancy.models import Agent
    from bonuses.models import BonusRule
    from django.db.models import Sum
    from django.utils import timezone
    import datetime

    # Bonus summary per agent (current month)
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    kpi_qs = KPIAgentDaily.objects.filter(
        tenant=tenant,
        kpi_date__gte=month_start.date(),
        kpi_date__lte=now.date(),
    ).values(
        'agent__id', 'agent__agent_code', 'agent__user__full_name'
    ).annotate(
        conversions=Sum('leads_converted'),
        totalSales=Sum('revenue_amount'),
        bonusAmount=Sum('bonus_amount'),
    ).order_by('-totalSales')

    bonus_summary = []
    for row in kpi_qs:
        bonus_summary.append({
            'agentName': row['agent__user__full_name'] or 'Unknown',
            'agentCode': row['agent__agent_code'] or '',
            'conversions': row['conversions'] or 0,
            'totalSales': float(row['totalSales'] or 0),
            'bonusAmount': float(row['bonusAmount'] or 0),
        })

    # Audit trail: recent sales with bonus info
    recent_sales = Sale.objects.filter(
        tenant=tenant
    ).select_related(
        'agent', 'agent__user', 'customer', 'product', 'lead'
    ).order_by('-sold_at')[:20]

    rules = list(BonusRule.objects.filter(tenant=tenant, is_active=True).order_by('id'))

    audit_trail = []
    for sale in recent_sales:
        matched_rule = rules[0] if rules else None
        for r in rules:
            if r.rule_dimension == 'SELL_AMOUNT' and sale.amount >= (r.num_from or 0):
                matched_rule = r
                break

        rule_name = matched_rule.name if matched_rule else 'N/A'
        rule_type = matched_rule.amount_type if matched_rule else 'N/A'
        if matched_rule and matched_rule.amount_type == 'percent_of_sale':
            bonus = float(sale.amount) * float(matched_rule.amount_value or 0) / 100
            formula = f'{sale.amount} x {matched_rule.amount_value}%'
        elif matched_rule and matched_rule.amount_type == 'fixed':
            bonus = float(matched_rule.amount_value or 0)
            formula = f'Fixed ${matched_rule.amount_value}'
        else:
            bonus = 0
            formula = 'N/A'

        audit_trail.append({
            'agentName': sale.agent.user.full_name if sale.agent and sale.agent.user else 'Unknown',
            'agentCode': sale.agent.agent_code if sale.agent else '',
            'leadId': f'LD-{sale.lead_id}' if sale.lead_id else 'N/A',
            'customerName': sale.customer.full_name if sale.customer else 'Unknown',
            'saleDate': sale.sold_at.strftime('%Y-%m-%d'),
            'saleAmount': float(sale.amount),
            'ruleName': rule_name,
            'ruleType': rule_type,
            'bonusAmount': bonus,
            'formula': formula,
        })

    return Response({
        'bonusSummary': bonus_summary,
        'auditTrail': audit_trail,
    })
