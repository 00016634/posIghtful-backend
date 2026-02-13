from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tenants', views.TenantViewSet, basename='tenant')
router.register(r'regions', views.RegionViewSet, basename='region')
router.register(r'cities', views.CityViewSet, basename='city')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'customers', views.CustomerViewSet, basename='customer')
router.register(r'agents', views.AgentViewSet, basename='agent')

urlpatterns = [
    path('', include(router.urls)),
]
