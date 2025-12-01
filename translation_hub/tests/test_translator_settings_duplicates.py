import frappe
from frappe.tests.utils import FrappeTestCase


class TestTranslatorSettingsDuplicates(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.settings = frappe.get_single("Translator Settings")
		self.settings.monitored_apps = []
		self.settings.default_languages = []
		self.settings.save()

	def test_remove_duplicate_monitored_apps(self):
		# Add duplicate apps
		self.settings.append("monitored_apps", {"source_app": "frappe"})
		self.settings.append("monitored_apps", {"source_app": "frappe"})
		self.settings.append("monitored_apps", {"source_app": "translation_hub"})
		self.settings.save()

		# Reload and check
		self.settings.reload()
		self.assertEqual(len(self.settings.monitored_apps), 2)
		apps = [row.source_app for row in self.settings.monitored_apps]
		self.assertIn("frappe", apps)
		self.assertIn("translation_hub", apps)
		self.assertEqual(apps.count("frappe"), 1)

	def test_remove_duplicate_languages(self):
		# Add duplicate languages
		self.settings.append(
			"default_languages",
			{"language_code": "pt-BR", "language_name": "Portuguese (Brazil)", "enabled": 1},
		)
		self.settings.append(
			"default_languages",
			{"language_code": "pt-BR", "language_name": "Portuguese (Brazil)", "enabled": 1},
		)
		self.settings.append(
			"default_languages", {"language_code": "es", "language_name": "Spanish", "enabled": 1}
		)
		self.settings.save()

		# Reload and check
		self.settings.reload()
		self.assertEqual(len(self.settings.default_languages), 2)
		langs = [row.language_code for row in self.settings.default_languages]
		self.assertIn("pt-BR", langs)
		self.assertIn("es", langs)
		self.assertEqual(langs.count("pt-BR"), 1)
