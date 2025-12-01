from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from translation_hub.core.config import TranslationConfig
from translation_hub.core.translation_service import GeminiService


class TestContextInjection(FrappeTestCase):
	def setUp(self):
		super().setUp()
		# Create a mock App with context
		self.app_name = "test_app_injection"
		# Mock installed apps to pass validation
		self.installed_apps_patcher = patch(
			"frappe.get_installed_apps",
			return_value=["frappe", "translation_hub", "test_app_injection", "erpnext"],
		)
		self.installed_apps_patcher.start()

		if not frappe.db.exists("App", self.app_name):
			self.app = frappe.get_doc(
				{
					"doctype": "App",
					"app_name": self.app_name,
					"app_title": "Translation Hub",
					"domain": "Logistics",
					"tone": "Formal",
					"description": "An ERP system for logistics.",
					"do_not_translate": [{"term": "HIMS"}],
				}
			).insert(ignore_permissions=True)
		else:
			self.app = frappe.get_doc("App", self.app_name)
			self.app.domain = "Logistics"
			self.app.tone = "Formal"
			self.app.description = "An ERP system for logistics."

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

		self.installed_apps_patcher.stop()
		super().tearDown()

	def test_fetch_context(self):
		config = TranslationConfig(api_key="test-key")
		service = GeminiService(config, app_name=self.app_name)

		context = service._fetch_context()

		self.assertEqual(context.get("domain"), "Logistics")
		self.assertEqual(context.get("tone"), "Formal")
		self.assertEqual(context.get("description"), "An ERP system for logistics.")

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

		self.assertIn("Domain: Healthcare", prompt)
		self.assertIn("Tone of Voice: Formal", prompt)
		self.assertIn("Patient: Paciente", prompt)
		self.assertIn("HIMS", prompt)
