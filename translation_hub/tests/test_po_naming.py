import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from translation_hub.tasks import execute_translation_job


class TestPONaming(FrappeTestCase):
	def setUp(self):
		self.app_name = "translation_hub"
		self.lang_code = "pt-BR"
		self.expected_po_filename = "pt_BR_test.po"
		self.production_po_filename = "pt_BR.po"

		# Ensure clean state
		self.app_path = frappe.get_app_path(self.app_name)
		self.locale_dir = Path(self.app_path) / "locale"
		self.po_path = self.locale_dir / self.expected_po_filename
		self.production_po_path = self.locale_dir / self.production_po_filename
		self.wrong_po_path = self.locale_dir / "pt-BR.po"

		if self.po_path.exists():
			os.remove(self.po_path)
		if self.production_po_path.exists():
			os.remove(self.production_po_path)
		if self.wrong_po_path.exists():
			os.remove(self.wrong_po_path)

		# Mock settings
		settings = frappe.get_single("Translator Settings")
		settings.api_key = "test-key"
		settings.append("monitored_apps", {"source_app": self.app_name})
		settings.append(
			"default_languages",
			{"language_code": self.lang_code, "language_name": "Portuguese (Brazil)", "enabled": 1},
		)
		settings.save(ignore_permissions=True)

		# Create a dummy job
		self.job = frappe.get_doc(
			{
				"doctype": "Translation Job",
				"source_app": self.app_name,
				"target_language": self.lang_code,
				"title": "Test PO Naming",
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		if self.po_path.exists():
			os.remove(self.po_path)
		if self.production_po_path.exists():
			os.remove(self.production_po_path)
		if self.wrong_po_path.exists():
			os.remove(self.wrong_po_path)
		self.job.delete(ignore_permissions=True)

	@patch("translation_hub.tasks.TranslationOrchestrator")
	@patch("translation_hub.tasks.ensure_pot_file")
	def test_po_file_creation_naming(self, mock_ensure_pot, mock_orchestrator):
		# Execute the job
		execute_translation_job(self.job.name)

		# Check if the correct file was passed to TranslationFile (via config)
		# We can inspect the arguments passed to TranslationConfig or TranslationFile
		# But since we patched Orchestrator, we can check its call args

		# Actually, TranslationFile is instantiated before Orchestrator.
		# Let's check if the file was created?
		# TranslationFile.__init__ creates the file if it doesn't exist.

		self.assertTrue(self.po_path.exists(), f"Test PO file {self.po_path} should exist")
		self.assertFalse(
			self.production_po_path.exists(),
			f"Production PO file {self.production_po_path} should NOT exist in test mode",
		)
		self.assertFalse(self.wrong_po_path.exists(), f"PO file {self.wrong_po_path} should NOT exist")
