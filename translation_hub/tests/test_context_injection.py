from unittest.mock import MagicMock

import frappe
from frappe.tests.utils import FrappeTestCase

from translation_hub.core.config import TranslationConfig
from translation_hub.core.translation_service import GeminiService


class TestContextInjection(FrappeTestCase):
	def setUp(self):
		super().setUp()
		# Create a mock App with context
		self.app_name = "translation_hub"
		if not frappe.db.exists("App", self.app_name):
			self.app = frappe.get_doc(
				{
					"doctype": "App",
					"app_name": self.app_name,
					"app_title": "Translation Hub",
					"domain": "Logistics",
					"tone": "Formal",
					"description": "An ERP system for logistics.",
					"glossary": [
						{"term": "Patient", "translation": "Paciente", "description": "Sick person"},
						{"term": "Doctor", "translation": "Médico"},
					],
					"do_not_translate": [{"term": "HIMS"}],
				}
			).insert(ignore_permissions=True)
		else:
			self.app = frappe.get_doc("App", self.app_name)
			self.app.domain = "Logistics"
			self.app.tone = "Formal"
			self.app.description = "An ERP system for logistics."
			self.app.set(
				"glossary",
				[
					{"term": "Patient", "translation": "Paciente", "description": "Sick person"},
					{"term": "Doctor", "translation": "Médico"},
				],
			)
			self.app.set("do_not_translate", [{"term": "HIMS"}])
			self.app.save(ignore_permissions=True)

	def tearDown(self):
		# Delete linked jobs first
		frappe.db.delete("Translation Job", {"source_app": self.app_name})

		# Clear monitored apps in Translator Settings
		settings = frappe.get_single("Translator Settings")
		settings.monitored_apps = [ma for ma in settings.monitored_apps if ma.source_app != self.app_name]
		settings.save(ignore_permissions=True)

		if frappe.db.exists("App", self.app_name):
			frappe.delete_doc("App", self.app_name)
		super().tearDown()

	def test_fetch_context(self):
		config = TranslationConfig(api_key="test-key")
		service = GeminiService(config, app_name=self.app_name)

		context = service._fetch_context()

		self.assertEqual(context.get("domain"), "Logistics")
		self.assertEqual(context.get("tone"), "Formal")
		self.assertEqual(context.get("description"), "An ERP system for logistics.")
		self.assertIn("Patient", context.get("glossary"))
		self.assertEqual(context["glossary"]["Patient"], "Paciente (Sick person)")
		self.assertEqual(context["glossary"]["Doctor"], "Médico")
		self.assertIn("HIMS", context.get("do_not_translate"))

	def test_prompt_injection(self):
		config = TranslationConfig(api_key="test-key")
		service = GeminiService(config, app_name=self.app_name)

		# Mock context to ensure we test prompt generation independently of fetch
		service.context = {
			"domain": "Healthcare",
			"tone": "Formal",
			"glossary": {"Patient": "Paciente"},
			"do_not_translate": ["HIMS"],
		}

		prompt = service._build_batch_prompt([{"msgid": "Hello"}])

		self.assertIn("Domínio: Healthcare", prompt)
		self.assertIn("Tom de Voz: Formal", prompt)
		self.assertIn("Patient: Paciente", prompt)
		self.assertIn("HIMS", prompt)
