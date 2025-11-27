from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from translation_hub.tasks import run_automated_translations


class TestAutomation(FrappeTestCase):
	def setUp(self):
		super().setUp()
		# Ensure Settings
		settings = frappe.get_single("Translator Settings")
		settings.enable_automated_translation = 1
		settings.monitored_apps = []
		settings.default_languages = []

		# Add monitored app (using translation_hub itself as it exists)
		settings.append("monitored_apps", {"source_app": "translation_hub"})

		# Add languages
		settings.append(
			"default_languages", {"language_code": "es", "language_name": "Spanish", "enabled": 1}
		)
		settings.append("default_languages", {"language_code": "fr", "language_name": "French", "enabled": 1})
		settings.save()

		# Clear existing jobs
		frappe.db.delete("Translation Job", {"source_app": "translation_hub"})

	def tearDown(self):
		super().tearDown()

	@patch("translation_hub.tasks.ensure_pot_file")
	@patch("translation_hub.core.translation_file.TranslationFile")
	def test_run_automated_translations(self, MockTranslationFile, mock_ensure_pot):
		# Mock TranslationFile to return untranslated entries so jobs are created
		instance = MockTranslationFile.return_value
		instance.get_untranslated_entries.return_value = [{"msgid": "Hello"}]

		# Run automation
		run_automated_translations()

		# Check jobs
		jobs = frappe.get_all(
			"Translation Job", fields=["target_language"], filters={"source_app": "translation_hub"}
		)
		languages = [j.target_language for j in jobs]

		self.assertIn("es", languages)
		self.assertIn("fr", languages)
		self.assertEqual(len(jobs), 2)
