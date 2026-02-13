from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'kpi', views.KPIAgentDailyViewSet, basename='kpi-agent-daily')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.dashboard_summary, name='dashboard-summary'),
]
