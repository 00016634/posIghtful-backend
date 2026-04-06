from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from users.models import User, Role, UserRole
from tenancy.models import Tenant, Region, City, Agent
from leads.models import Lead
from conversation_analysis.models import LeadConversation
from conversation_analysis.services import process_conversation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_AI_RESPONSE = {
    "rating": 4,
    "conversation_topic": "Product pricing inquiry",
    "short_description": "Customer asked about pricing and features. Agent provided details.",
    "conversation_outcome": "Customer showed interest and requested a follow-up.",
    "customer_sentiment": "positive",
}


class BaseTestMixin:
    """Shared setup for all test cases."""

    def _create_tenant(self, name="Test Company", code="TEST01"):
        return Tenant.objects.create(name=name, code=code, is_active=True)

    def _create_region(self, tenant):
        return Region.objects.create(tenant=tenant, name="Tashkent")

    def _create_city(self, tenant, region):
        return City.objects.create(tenant=tenant, region=region, name="Tashkent City")

    def _create_user(self, tenant, username="agent1", phone="+998901234567"):
        return User.objects.create_user(
            username=username,
            email=f"{username}@test.com",
            phone_number=phone,
            password="testpass123",
            tenant=tenant,
            full_name=f"User {username}",
        )

    def _create_role(self, code="AGENT", name="Agent"):
        role, _ = Role.objects.get_or_create(code=code, defaults={"name": name})
        return role

    def _assign_role(self, tenant, user, role_code):
        role = self._create_role(role_code, role_code.title())
        return UserRole.objects.create(tenant=tenant, user=user, role=role)

    def _create_agent(self, tenant, user, region, city, code="AG001", parent=None):
        return Agent.objects.create(
            tenant=tenant, user=user, agent_code=code,
            region=region, city=city, parent=parent, status="active",
        )

    def _create_lead(self, tenant, agent=None, name="John Doe", phone="+998909876543"):
        return Lead.objects.create(
            tenant=tenant, agent=agent,
            customer_name=name, customer_phone=phone,
        )

    def _setup_full(self):
        """Create tenant, region, city, user, agent, role, lead."""
        self.tenant = self._create_tenant()
        self.region = self._create_region(self.tenant)
        self.city = self._create_city(self.tenant, self.region)
        self.user = self._create_user(self.tenant)
        self.agent = self._create_agent(
            self.tenant, self.user, self.region, self.city
        )
        self._assign_role(self.tenant, self.user, "AGENT")
        self.lead = self._create_lead(self.tenant, self.agent)


# ===========================================================================
# MODEL TESTS
# ===========================================================================

class LeadConversationModelTest(BaseTestMixin, TestCase):

    def setUp(self):
        self._setup_full()

    def test_create_email_conversation(self):
        conv = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email",
            raw_transcript="Hello, I want to know about your products.",
        )
        self.assertEqual(conv.channel, "email")
        self.assertEqual(conv.transcription_status, "pending")
        self.assertEqual(conv.analysis_status, "pending")
        self.assertIsNone(conv.rating)
        self.assertIsNotNone(conv.created_at)

    def test_str_representation(self):
        conv = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="phone", raw_transcript="test",
        )
        self.assertIn("phone", str(conv))
        self.assertIn(str(self.lead.id), str(conv))

    def test_one_to_one_constraint(self):
        """Each lead can only have one conversation."""
        LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email", raw_transcript="First conversation",
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            LeadConversation.objects.create(
                tenant=self.tenant, lead=self.lead, agent=self.agent,
                channel="phone", raw_transcript="Second conversation",
            )

    def test_ordering_is_newest_first(self):
        lead2 = self._create_lead(self.tenant, self.agent, "Jane", "+998907777777")
        c1 = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email", raw_transcript="First",
        )
        c2 = LeadConversation.objects.create(
            tenant=self.tenant, lead=lead2, agent=self.agent,
            channel="email", raw_transcript="Second",
        )
        convs = list(LeadConversation.objects.all())
        self.assertEqual(convs[0].id, c2.id)
        self.assertEqual(convs[1].id, c1.id)


# ===========================================================================
# SERIALIZER VALIDATION TESTS
# ===========================================================================

class SerializerValidationTest(BaseTestMixin, TestCase):

    def setUp(self):
        self._setup_full()

    def test_email_requires_transcript(self):
        from conversation_analysis.serializers import LeadConversationCreateSerializer
        ser = LeadConversationCreateSerializer(data={
            "lead": self.lead.id,
            "channel": "email",
            # no raw_transcript
        })
        self.assertFalse(ser.is_valid())

    def test_email_with_transcript_valid(self):
        from conversation_analysis.serializers import LeadConversationCreateSerializer
        ser = LeadConversationCreateSerializer(data={
            "lead": self.lead.id,
            "channel": "email",
            "raw_transcript": "Hello, I need pricing info.",
        })
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_online_chat_requires_transcript(self):
        from conversation_analysis.serializers import LeadConversationCreateSerializer
        ser = LeadConversationCreateSerializer(data={
            "lead": self.lead.id,
            "channel": "online_chat",
        })
        self.assertFalse(ser.is_valid())

    def test_phone_requires_audio_or_transcript(self):
        from conversation_analysis.serializers import LeadConversationCreateSerializer
        ser = LeadConversationCreateSerializer(data={
            "lead": self.lead.id,
            "channel": "phone",
        })
        self.assertFalse(ser.is_valid())

    def test_phone_with_transcript_valid(self):
        from conversation_analysis.serializers import LeadConversationCreateSerializer
        ser = LeadConversationCreateSerializer(data={
            "lead": self.lead.id,
            "channel": "phone",
            "raw_transcript": "Agent: Hello! Customer: Hi, I want to buy.",
        })
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_in_person_with_transcript_valid(self):
        from conversation_analysis.serializers import LeadConversationCreateSerializer
        ser = LeadConversationCreateSerializer(data={
            "lead": self.lead.id,
            "channel": "in_person",
            "raw_transcript": "Face to face discussion.",
        })
        self.assertTrue(ser.is_valid(), ser.errors)


# ===========================================================================
# SERVICE LAYER TESTS (mocked OpenAI)
# ===========================================================================

class ProcessConversationServiceTest(BaseTestMixin, TestCase):

    def setUp(self):
        self._setup_full()

    @patch("conversation_analysis.services.analyze_conversation")
    def test_email_conversation_analysis(self, mock_analyze):
        """Email channel should skip transcription and go straight to analysis."""
        mock_analyze.return_value = MOCK_AI_RESPONSE

        conv = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email",
            raw_transcript="Customer: What's the price? Agent: $500 per unit.",
        )
        process_conversation(conv)
        conv.refresh_from_db()

        self.assertEqual(conv.transcription_status, "skipped")
        self.assertEqual(conv.analysis_status, "completed")
        self.assertEqual(conv.rating, 4)
        self.assertEqual(conv.customer_sentiment, "positive")
        self.assertIn("Product pricing", conv.conversation_topic)
        self.assertIsNotNone(conv.analyzed_at)
        mock_analyze.assert_called_once()

    @patch("conversation_analysis.services.analyze_conversation")
    def test_online_chat_analysis(self, mock_analyze):
        mock_analyze.return_value = MOCK_AI_RESPONSE

        conv = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="online_chat",
            raw_transcript="Chat transcript here.",
        )
        process_conversation(conv)
        conv.refresh_from_db()

        self.assertEqual(conv.transcription_status, "skipped")
        self.assertEqual(conv.analysis_status, "completed")
        self.assertEqual(conv.rating, 4)

    @patch("conversation_analysis.services.analyze_conversation")
    def test_phone_with_transcript_no_audio_analyzed(self, mock_analyze):
        """Phone with raw_transcript but no audio should still analyze successfully."""
        mock_analyze.return_value = MOCK_AI_RESPONSE

        conv = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="phone",
            raw_transcript="Manual phone transcript.",
        )
        process_conversation(conv)
        conv.refresh_from_db()

        # No audio file, but transcript exists → transcription not needed
        # Analysis should still complete since raw_transcript is present
        self.assertEqual(conv.analysis_status, "completed")
        self.assertEqual(conv.rating, 4)

    def test_phone_no_audio_no_transcript_fails(self):
        """Phone with neither audio nor transcript should fail."""
        conv = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="phone",
        )
        process_conversation(conv)
        conv.refresh_from_db()

        self.assertEqual(conv.transcription_status, "failed")
        self.assertEqual(conv.analysis_status, "failed")

    @patch("conversation_analysis.services.analyze_conversation")
    def test_analysis_failure_sets_failed_status(self, mock_analyze):
        mock_analyze.side_effect = Exception("OpenAI API error")

        conv = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email",
            raw_transcript="Some transcript.",
        )
        process_conversation(conv)
        conv.refresh_from_db()

        self.assertEqual(conv.analysis_status, "failed")
        self.assertIsNone(conv.rating)

    @patch("conversation_analysis.services.analyze_conversation")
    def test_ai_raw_response_stored(self, mock_analyze):
        mock_analyze.return_value = MOCK_AI_RESPONSE

        conv = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email",
            raw_transcript="Test transcript.",
        )
        process_conversation(conv)
        conv.refresh_from_db()

        self.assertEqual(conv.ai_raw_response, MOCK_AI_RESPONSE)


# ===========================================================================
# API ENDPOINT TESTS
# ===========================================================================

class ConversationAPITest(BaseTestMixin, APITestCase):

    def setUp(self):
        self._setup_full()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    # -- CREATE --

    @patch("conversation_analysis.views.process_conversation")
    def test_create_email_conversation(self, mock_process):
        response = self.client.post("/api/conversations/", {
            "lead": self.lead.id,
            "channel": "email",
            "raw_transcript": "Customer asked about pricing via email.",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["lead"], self.lead.id)
        self.assertEqual(response.data["channel"], "email")
        mock_process.assert_called_once()

    @patch("conversation_analysis.views.process_conversation")
    def test_create_online_chat_conversation(self, mock_process):
        response = self.client.post("/api/conversations/", {
            "lead": self.lead.id,
            "channel": "online_chat",
            "raw_transcript": "Chat: Hi! Agent: How can I help?",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_email_without_transcript_fails(self):
        response = self.client.post("/api/conversations/", {
            "lead": self.lead.id,
            "channel": "email",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_phone_without_data_fails(self):
        response = self.client.post("/api/conversations/", {
            "lead": self.lead.id,
            "channel": "phone",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("conversation_analysis.views.process_conversation")
    def test_create_auto_assigns_tenant_and_agent(self, mock_process):
        response = self.client.post("/api/conversations/", {
            "lead": self.lead.id,
            "channel": "email",
            "raw_transcript": "Test transcript.",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        conv = LeadConversation.objects.get(id=response.data["id"])
        self.assertEqual(conv.tenant_id, self.tenant.id)
        self.assertEqual(conv.agent_id, self.agent.id)

    @patch("conversation_analysis.views.process_conversation")
    def test_create_duplicate_lead_fails(self, mock_process):
        """OneToOne: second conversation for same lead should fail."""
        self.client.post("/api/conversations/", {
            "lead": self.lead.id,
            "channel": "email",
            "raw_transcript": "First conversation.",
        })
        response = self.client.post("/api/conversations/", {
            "lead": self.lead.id,
            "channel": "email",
            "raw_transcript": "Second conversation.",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- LIST --

    @patch("conversation_analysis.views.process_conversation")
    def test_list_conversations(self, mock_process):
        LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email", raw_transcript="Test",
        )
        response = self.client.get("/api/conversations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    # -- DETAIL --

    def test_get_conversation_detail(self):
        conv = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email", raw_transcript="Detail test",
            rating=4, customer_sentiment="positive",
            conversation_topic="Pricing", analysis_status="completed",
        )
        response = self.client.get(f"/api/conversations/{conv.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rating"], 4)
        self.assertEqual(response.data["customer_sentiment"], "positive")
        self.assertEqual(response.data["lead_customer_name"], "John Doe")
        self.assertEqual(response.data["agent_name"], "User agent1")

    # -- BY LEAD --

    def test_get_conversation_by_lead(self):
        LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email", raw_transcript="By lead test",
        )
        response = self.client.get(f"/api/conversations/by-lead/{self.lead.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["lead"], self.lead.id)

    def test_by_lead_not_found(self):
        response = self.client.get("/api/conversations/by-lead/99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- ANALYZE ACTION --

    @patch("conversation_analysis.views.process_conversation")
    def test_analyze_action(self, mock_process):
        conv = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email", raw_transcript="Re-analyze this.",
            analysis_status="failed",
        )
        response = self.client.post(f"/api/conversations/{conv.id}/analyze/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_process.assert_called_once()

    @patch("conversation_analysis.views.process_conversation")
    def test_analyze_resets_status(self, mock_process):
        conv = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email", raw_transcript="Re-analyze.",
            analysis_status="completed", rating=3,
        )
        self.client.post(f"/api/conversations/{conv.id}/analyze/")
        # process_conversation is called; before that, status was reset to pending
        mock_process.assert_called_once()
        # Check the conversation passed to process_conversation had reset status
        called_conv = mock_process.call_args[0][0]
        self.assertEqual(called_conv.analysis_status, "pending")

    # -- UNAUTHENTICATED --

    def test_unauthenticated_access_denied(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/conversations/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- FILTERING --

    def test_filter_by_channel(self):
        LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email", raw_transcript="Email conv",
        )
        response = self.client.get("/api/conversations/?channel=email")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for r in response.data["results"]:
            self.assertEqual(r["channel"], "email")

    def test_filter_by_sentiment(self):
        LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email", raw_transcript="Happy conv",
            customer_sentiment="positive", analysis_status="completed",
        )
        response = self.client.get("/api/conversations/?customer_sentiment=positive")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_by_topic(self):
        LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead, agent=self.agent,
            channel="email", raw_transcript="test",
            conversation_topic="Special Pricing Deal",
        )
        response = self.client.get("/api/conversations/?search=Special Pricing")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)


# ===========================================================================
# ROLE-BASED ACCESS TESTS
# ===========================================================================

class RoleBasedAccessTest(BaseTestMixin, APITestCase):
    """Test that agents only see their own, supervisors see team, managers see all."""

    def setUp(self):
        self.tenant = self._create_tenant()
        self.region = self._create_region(self.tenant)
        self.city = self._create_city(self.tenant, self.region)

        # Agent 1
        self.user1 = self._create_user(self.tenant, "agent1", "+998901111111")
        self.agent1 = self._create_agent(
            self.tenant, self.user1, self.region, self.city, "AG001"
        )
        self._assign_role(self.tenant, self.user1, "AGENT")

        # Agent 2
        self.user2 = self._create_user(self.tenant, "agent2", "+998902222222")
        self.agent2 = self._create_agent(
            self.tenant, self.user2, self.region, self.city, "AG002"
        )
        self._assign_role(self.tenant, self.user2, "AGENT")

        # Supervisor (parent of agent1)
        self.supervisor_user = self._create_user(self.tenant, "supervisor1", "+998903333333")
        self.supervisor_agent = self._create_agent(
            self.tenant, self.supervisor_user, self.region, self.city, "SUP001"
        )
        self._assign_role(self.tenant, self.supervisor_user, "SUPERVISOR")
        # Set agent1's parent to supervisor
        self.agent1.parent = self.supervisor_agent
        self.agent1.save()

        # Manager
        self.manager_user = self._create_user(self.tenant, "manager1", "+998904444444")
        self._assign_role(self.tenant, self.manager_user, "MANAGER")

        # Create leads and conversations
        self.lead1 = self._create_lead(self.tenant, self.agent1, "Customer A", "+998911111111")
        self.lead2 = self._create_lead(self.tenant, self.agent2, "Customer B", "+998922222222")
        self.lead_sup = self._create_lead(self.tenant, self.supervisor_agent, "Customer C", "+998933333333")

        self.conv1 = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead1, agent=self.agent1,
            channel="email", raw_transcript="Agent1 conversation",
        )
        self.conv2 = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead2, agent=self.agent2,
            channel="email", raw_transcript="Agent2 conversation",
        )
        self.conv_sup = LeadConversation.objects.create(
            tenant=self.tenant, lead=self.lead_sup, agent=self.supervisor_agent,
            channel="email", raw_transcript="Supervisor conversation",
        )

        self.client = APIClient()

    def test_agent_sees_only_own_conversations(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/conversations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(self.conv1.id, ids)
        self.assertNotIn(self.conv2.id, ids)
        self.assertNotIn(self.conv_sup.id, ids)

    def test_supervisor_sees_own_and_team(self):
        self.client.force_authenticate(user=self.supervisor_user)
        response = self.client.get("/api/conversations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data["results"]]
        # Supervisor sees: own + agent1 (supervised)
        self.assertIn(self.conv1.id, ids)       # agent1 is supervised
        self.assertIn(self.conv_sup.id, ids)    # own
        self.assertNotIn(self.conv2.id, ids)    # agent2 not supervised

    def test_manager_sees_all_tenant_conversations(self):
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.get("/api/conversations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(self.conv1.id, ids)
        self.assertIn(self.conv2.id, ids)
        self.assertIn(self.conv_sup.id, ids)

    def test_cross_tenant_isolation(self):
        """Users from another tenant should not see conversations."""
        tenant2 = self._create_tenant("Other Co", "OTHER01")
        region2 = self._create_region(tenant2)
        city2 = self._create_city(tenant2, region2)
        other_user = self._create_user(tenant2, "other_agent", "+998905555555")
        self._create_agent(tenant2, other_user, region2, city2, "OT001")
        self._assign_role(tenant2, other_user, "MANAGER")

        self.client.force_authenticate(user=other_user)
        response = self.client.get("/api/conversations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)
