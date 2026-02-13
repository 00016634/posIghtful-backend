from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'policies', views.CommissionPolicyViewSet, basename='commission-policy')
router.register(r'rules', views.BonusRuleViewSet, basename='bonus-rule')

urlpatterns = [
    path('', include(router.urls)),
]
