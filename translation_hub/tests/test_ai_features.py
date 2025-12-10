import unittest
from unittest.mock import MagicMock, patch

import frappe

from translation_hub.core.config import TranslationConfig
from translation_hub.translation_hub.doctype.translation_review.translation_review import (
	create_bulk_reviews,
	get_ai_suggestion,
)


class TestAIFeatures(unittest.TestCase):
	def setUp(self):
		# Setup prerequisites
		self.source_app = "erpnext"
		self.language = "pt-BR"

		# Ensure settings exist
		if not frappe.db.exists("Translator Settings", "Translator Settings"):
			doc = frappe.new_doc("Translator Settings")
			doc.llm_provider = "Gemini"
			doc.api_key = "test-key"
			doc.save()
		else:
			doc = frappe.get_single("Translator Settings")
			doc.llm_provider = "Gemini"
			doc.api_key = "test-key"
			doc.save()

		# Create dummy Translation
		frappe.db.delete("Translation", {"source_text": "Test AI Source"})
		frappe.get_doc(
			{
				"doctype": "Translation",
				"source_text": "Test AI Source",
				"translated_text": "Bad Translation",
				"language": "pt-BR",
			}
		).insert()

		# Clear reviews
		frappe.db.delete("Translation Review", {"source_text": "Test AI Source"})

	def test_config_init(self):
		"""Verify TranslationConfig accepts provider argument."""
		config = TranslationConfig(language_code="pt-BR", api_key="test", provider="Groq")
		self.assertEqual(config.provider, "Groq")

	@patch("translation_hub.core.translation_service.GeminiService")
	def test_create_bulk_reviews_with_ai(self, MockService):
		# Mock Service
		instance = MockService.return_value
		instance.translate.return_value = [{"msgid": "Test AI Source", "msgstr": "AI Suggested Text"}]

		# Execute
		create_bulk_reviews(self.source_app, self.language, "Test AI", use_ai=True, ai_context="Formal")

		# Verify
		review_name = frappe.db.get_value("Translation Review", {"source_text": "Test AI Source"})
		self.assertTrue(review_name)

		review = frappe.get_doc("Translation Review", review_name)
		self.assertEqual(review.suggested_text, "AI Suggested Text")
		self.assertEqual(review.status, "Pending")

	@patch("translation_hub.core.translation_service.GeminiService")
	def test_get_ai_suggestion(self, MockService):
		# Mock Service
		instance = MockService.return_value
		instance.translate.return_value = [{"msgid": "Any Source", "msgstr": "Better Suggestion"}]

		# Execute
		suggestion = get_ai_suggestion("Any Source", "pt-BR", "erpnext", context="Brief")

		# Verify
		self.assertEqual(suggestion, "Better Suggestion")

	def tearDown(self):
		frappe.db.rollback()
