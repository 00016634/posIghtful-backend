from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'kpi', views.KPIAgentDailyViewSet, basename='kpi-agent-daily')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.dashboard_summary, name='dashboard-summary'),
    path('agent-dashboard/', views.agent_dashboard, name='agent-dashboard'),
    path('supervisor-dashboard/', views.supervisor_dashboard, name='supervisor-dashboard'),
    path('manager-dashboard/', views.manager_dashboard, name='manager-dashboard'),
    path('conversion-chart/', views.conversion_chart, name='conversion-chart'),
    path('revenue-trend/', views.revenue_trend, name='revenue-trend'),
    path('personnel-chart/', views.personnel_chart, name='personnel-chart'),
    path('conversion-rate-trend/', views.conversion_rate_trend, name='conversion-rate-trend'),
    path('supervisor-performance/', views.supervisor_performance, name='supervisor-performance'),
    path('top-agents/', views.top_agents, name='top-agents'),
    path('performance-chart/', views.performance_chart, name='performance-chart'),
]
