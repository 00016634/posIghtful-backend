from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'policies', views.CommissionPolicyViewSet, basename='commission-policy')
router.register(r'rules', views.BonusRuleViewSet, basename='bonus-rule')
router.register(r'ledger', views.BonusLedgerViewSet, basename='bonus-ledger')

urlpatterns = [
    path('', include(router.urls)),
    path('monthly/', views.monthly_bonuses_view, name='monthly-bonuses'),
    path('monthly/<str:month>/', views.monthly_bonus_detail_view, name='monthly-bonus-detail'),
    path('monthly/<str:month>/audit/', views.monthly_audit_view, name='monthly-audit'),
]
