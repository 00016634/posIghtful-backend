from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')

urlpatterns = [
    # Authentication endpoints
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User profile endpoints
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password_view, name='change_password'),

    # Roles
    path('roles/', views.role_list_view, name='roles'),

    # Admin / management endpoints
    path('admin-stats/', views.admin_stats_view, name='admin-stats'),
    path('recent-activity/', views.recent_activity_view, name='recent-activity'),
    path('accountant-data/', views.accountant_data_view, name='accountant-data'),

    # User CRUD (via router)
    path('', include(router.urls)),
]
