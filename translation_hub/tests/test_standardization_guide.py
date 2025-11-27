import frappe
from frappe.tests.utils import FrappeTestCase
from translation_hub.tasks import execute_translation_job
from unittest.mock import MagicMock, patch

class TestStandardizationGuide(FrappeTestCase):
	def test_composite_guide_logic(self):
		# Mock settings
		settings = MagicMock()
		settings.standardization_guide = "Global Rule"
		settings.get_password.return_value = "test-key"
		settings.use_database_storage = 1
		settings.save_to_po_file = 0
		settings.export_po_on_complete = 0
		
		# Mock monitored app row
		app_row = MagicMock()
		app_row.source_app = "translation_hub"
		app_row.target_language = "pt-BR"
		app_row.standardization_guide = "App Rule"
		settings.monitored_apps = [app_row]

		# Mock language row
		lang_row = MagicMock()
		lang_row.language_code = "pt-BR"
		lang_row.standardization_guide = "Language Rule"
		settings.default_languages = [lang_row]

		# Mock Job
		job = MagicMock()
		job.source_app = "translation_hub"
		job.target_language = "pt-BR"
		job.name = "Test Job"

		# Patch everything
		with patch("frappe.get_doc", return_value=job), \
			 patch("frappe.get_single", return_value=settings), \
			 patch("translation_hub.tasks.TranslationConfig") as MockConfig, \
			 patch("translation_hub.tasks.TranslationOrchestrator"), \
			 patch("translation_hub.tasks.TranslationFile"), \
			 patch("translation_hub.tasks.DocTypeLogger"), \
			 patch("translation_hub.tasks.get_app_path", return_value="/tmp"), \
			 patch("os.path.join", return_value="/tmp/file"), \
			 patch("frappe.utils.now_datetime", return_value="2025-01-01 12:00:00"):
			
			try:
				execute_translation_job("Test Job")
			except Exception as e:
				print(f"Caught exception: {e}")

			# Verify Config was initialized with Composite Guide
			args, kwargs = MockConfig.call_args
			guide = kwargs.get('standardization_guide')
			
			# Verify all parts are present
			self.assertIn("Global Guide (System Prompt)", guide)
			self.assertIn("App Rule", guide)
			self.assertIn("Language Rule", guide)
			
			# Verify System Prompt content (partial match)
			self.assertIn("Frappe Framework", guide)
			self.assertIn("Core Principles", guide)
