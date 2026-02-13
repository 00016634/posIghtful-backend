from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'pipelines', views.LeadPipelineViewSet, basename='lead-pipeline')
router.register(r'stages', views.LeadStageViewSet, basename='lead-stage')
router.register(r'leads', views.LeadViewSet, basename='lead')
router.register(r'applications', views.LeadApplicationViewSet, basename='lead-application')
router.register(r'stage-history', views.LeadStageHistoryViewSet, basename='lead-stage-history')

urlpatterns = [
    path('', include(router.urls)),
]
