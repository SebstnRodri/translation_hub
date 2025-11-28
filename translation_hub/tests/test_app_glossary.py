# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestAppGlossary(FrappeTestCase):
	def setUp(self):
		# Create test App Glossary
		if not frappe.db.exists("App", "translation_hub"):
			frappe.get_doc(
				{"doctype": "App", "app_name": "translation_hub", "app_title": "Translation Hub"}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Language", "pt-BR"):
			frappe.get_doc(
				{"doctype": "Language", "language_code": "pt-BR", "language_name": "Portuguese (Brazil)"}
			).insert(ignore_permissions=True)

		# Clean up existing glossaries for test isolation
		existing_glossaries = frappe.get_all(
			"App Glossary", filters={"app": "translation_hub", "language": "pt-BR"}
		)
		for g in existing_glossaries:
			frappe.delete_doc("App Glossary", g.name, force=True)

		self.glossary = frappe.get_doc(
			{
				"doctype": "App Glossary",
				"app": "translation_hub",
				"language": "pt-BR",
				"glossary_items": [
					{"term": "Test Term", "translation": "Termo de Teste", "description": "Contexto de teste"}
				],
			}
		).insert(ignore_permissions=True)

		# Ensure settings exist and configure monitored app
		if not frappe.db.exists("Translator Settings", "Translator Settings"):
			settings = frappe.get_single("Translator Settings")
		else:
			settings = frappe.get_doc("Translator Settings", "Translator Settings")

		settings.api_key = "test-key"
		settings.append("monitored_apps", {"source_app": "translation_hub", "target_language": "pt-BR"})
		settings.append(
			"default_languages",
			{"language_code": "pt-BR", "language_name": "Portuguese (Brazil)", "enabled": 1},
		)
		settings.save(ignore_permissions=True)

		self.job = frappe.get_doc(
			{
				"doctype": "Translation Job",
				"title": "Glossary Test Job",
				"source_app": "translation_hub",
				"target_language": "pt-BR",
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		self.glossary.delete(ignore_permissions=True)
		self.job.delete(ignore_permissions=True)

	@patch("translation_hub.tasks.TranslationOrchestrator")
	@patch("translation_hub.tasks.TranslationConfig")
	@patch("translation_hub.tasks.ensure_pot_file")
	def test_glossary_inclusion(self, mock_ensure_pot, mock_config, mock_orchestrator):
		from translation_hub.tasks import execute_translation_job

		# Mock settings to avoid API key issues
		settings = frappe.get_single("Translator Settings")
		settings.api_key = "test-key"
		settings.save(ignore_permissions=True)

		execute_translation_job(self.job.name)

		# Check if config was initialized with glossary
		call_args = mock_config.call_args
		self.assertIsNotNone(call_args)

		kwargs = call_args[1]
		standardization_guide = kwargs.get("standardization_guide", "")

		self.assertIn("Glossary Terms:", standardization_guide)
		self.assertIn("- Test Term: Termo de Teste (Contexto de teste)", standardization_guide)
