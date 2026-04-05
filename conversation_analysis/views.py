import logging

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import LeadConversation
from .serializers import LeadConversationSerializer, LeadConversationCreateSerializer
from .services import process_conversation

logger = logging.getLogger(__name__)


class LeadConversationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['agent', 'channel', 'customer_sentiment', 'rating', 'analysis_status']
    search_fields = ['conversation_topic', 'short_description', 'lead__customer_name']
    ordering_fields = ['created_at', 'rating', 'analyzed_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return LeadConversationCreateSerializer
        return LeadConversationSerializer

    def get_queryset(self):
        qs = LeadConversation.objects.select_related(
            'tenant', 'lead', 'agent', 'agent__user',
        ).all()

        user = self.request.user
        if not user.tenant_id:
            return qs

        qs = qs.filter(tenant=user.tenant)

        # Role-based filtering
        from users.models import UserRole
        user_roles = set(
            UserRole.objects.filter(user=user, tenant=user.tenant)
            .values_list('role__code', flat=True)
        )

        # Managers and admins see everything in their tenant
        if user_roles & {'MANAGER', 'ADMIN', 'FINANCE'}:
            return qs

        # Supervisors see their team's conversations
        if 'SUPERVISOR' in user_roles:
            from tenancy.models import Agent
            supervised_agents = Agent.objects.filter(
                parent__user=user, tenant=user.tenant,
            ).values_list('id', flat=True)
            # Include own agent record too
            own_agent = Agent.objects.filter(user=user, tenant=user.tenant).values_list('id', flat=True)
            agent_ids = list(supervised_agents) + list(own_agent)
            return qs.filter(agent_id__in=agent_ids)

        # Agents see only their own
        from tenancy.models import Agent
        agent = Agent.objects.filter(user=user, tenant=user.tenant).first()
        if agent:
            return qs.filter(agent=agent)

        return qs.none()

    def perform_create(self, serializer):
        from tenancy.models import Agent

        user = self.request.user
        kwargs = {}

        if user.tenant_id:
            kwargs['tenant'] = user.tenant

        # Auto-assign agent from logged-in user
        agent = Agent.objects.filter(user=user, tenant=user.tenant).first()
        if agent:
            kwargs['agent'] = agent

        conversation = serializer.save(**kwargs)

        # Trigger AI processing
        try:
            process_conversation(conversation)
        except Exception as e:
            logger.error(f"Failed to process conversation {conversation.id}: {e}")

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """Manually trigger or re-trigger AI analysis."""
        conversation = self.get_object()

        # Reset statuses
        conversation.analysis_status = 'pending'
        if conversation.channel in ('in_person', 'phone') and conversation.audio_file and not conversation.raw_transcript:
            conversation.transcription_status = 'pending'
        conversation.save()

        try:
            process_conversation(conversation)
            conversation.refresh_from_db()
            serializer = LeadConversationSerializer(conversation)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Analysis failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_by_lead(request, lead_id):
    """Get conversation analysis for a specific lead."""
    user = request.user
    try:
        conversation = LeadConversation.objects.select_related(
            'tenant', 'lead', 'agent', 'agent__user',
        ).get(lead_id=lead_id, tenant=user.tenant)
    except LeadConversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found for this lead'},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = LeadConversationSerializer(conversation)
    return Response(serializer.data)
