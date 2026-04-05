from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.LeadConversationViewSet, basename='lead-conversation')

urlpatterns = [
    path('by-lead/<int:lead_id>/', views.conversation_by_lead, name='conversation-by-lead'),
    path('', include(router.urls)),
]
