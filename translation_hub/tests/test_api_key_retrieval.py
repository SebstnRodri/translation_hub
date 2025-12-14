"""
Tests for API Key Retrieval (v1.6.1 Critical Fix)

Ensures that each LLM provider retrieves only its own API key,
preventing the ValidationError that occurred when Groq/OpenRouter
tried to use Gemini's api_key field.
"""

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestAPIKeyRetrieval(FrappeTestCase):
	"""Test correct API key retrieval for each provider"""

	def setUp(self):
		# Create test settings with all API keys
		self.settings = frappe.get_single("Translator Settings")

	def tearDown(self):
		frappe.db.rollback()

	def test_gemini_provider_uses_api_key(self):
		"""Test that Gemini provider uses api_key field"""
		self.settings.llm_provider = "Gemini"
		self.settings.set("api_key", "test-gemini-key")
		self.settings.save()

		# Should be able to retrieve Gemini key without error
		api_key = self.settings.get_password("api_key")
		self.assertEqual(api_key, "test-gemini-key")

	def test_groq_provider_uses_groq_api_key(self):
		"""Test that Groq provider uses groq_api_key field"""
		self.settings.llm_provider = "Groq"
		self.settings.set("groq_api_key", "test-groq-key")
		self.settings.save()

		# Should be able to retrieve Groq key without error
		api_key = self.settings.get_password("groq_api_key")
		self.assertEqual(api_key, "test-groq-key")

	def test_openrouter_provider_uses_openrouter_api_key(self):
		"""Test that OpenRouter provider uses openrouter_api_key field"""
		self.settings.llm_provider = "OpenRouter"
		self.settings.set("openrouter_api_key", "test-openrouter-key")
		self.settings.save()

		# Should be able to retrieve OpenRouter key without error
		api_key = self.settings.get_password("openrouter_api_key")
		self.assertEqual(api_key, "test-openrouter-key")

	def test_provider_no_cross_contamination(self):
		"""Test each provider only fetches its own key"""
		# Set different keys for each provider
		self.settings.set("api_key", "gemini-123")
		self.settings.set("groq_api_key", "groq-456")
		self.settings.set("openrouter_api_key", "openrouter-789")
		self.settings.save()

		# Test Groq doesn't fetch Gemini key
		self.settings.llm_provider = "Groq"
		groq_key = self.settings.get_password("groq_api_key")
		self.assertEqual(groq_key, "groq-456")
		self.assertNotEqual(groq_key, "gemini-123")

		# Test OpenRouter doesn't fetch Gemini key
		self.settings.llm_provider = "OpenRouter"
		or_key = self.settings.get_password("openrouter_api_key")
		self.assertEqual(or_key, "openrouter-789")
		self.assertNotEqual(or_key, "gemini-123")
