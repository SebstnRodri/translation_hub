import json
import logging
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from translation_hub.core.config import TranslationConfig
from translation_hub.core.orchestrator import TranslationOrchestrator
from translation_hub.tasks import backup_translations, extract_custom_messages


class TestFeaturesV123(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.temp_dir = Path(frappe.get_site_path("private", "test_v123"))
		if self.temp_dir.exists():
			shutil.rmtree(self.temp_dir)
		self.temp_dir.mkdir(parents=True)

	def tearDown(self):
		if self.temp_dir.exists():
			shutil.rmtree(self.temp_dir)
		super().tearDown()

	# --- 1. Test JSONDecodeError Fix ---
	def test_backup_with_empty_string_apps(self):
		"""
		Verifies that passing apps="" or apps=None to backup_translations
		does NOT raise JSONDecodeError.
		"""
		# Ensure settings have a URL so validation passes
		frappe.get_doc("Translator Settings").db_set("backup_repo_url", "https://example.com/repo.git")

		# Patch the source class since it's imported locally in the task
		with patch("translation_hub.core.git_sync_service.GitSyncService") as MockService:
			# Should not raise error
			backup_translations(apps="")
			backup_translations(apps=None)

			# Verify calls were made. calling backup() on the instance returned by constructor.
			MockService.return_value.backup.assert_called()

	# --- 2. Test Dashboard Custom Extraction ---
	def test_dashboard_extraction(self):
		"""
		Verifies that extract_custom_messages correctly finds label fields
		in Number Card JSON files.
		"""
		# Create a dummy structure: app_name/module/number_card/my_card/my_card.json
		app_name = "test_app_extraction"
		app_dir = self.temp_dir / app_name
		card_dir = app_dir / "module" / "number_card" / "my_card"
		card_dir.mkdir(parents=True)

		json_file = card_dir / "my_card.json"
		json_content = {"doctype": "Number Card", "label": "Test Dashboard Label", "type": "Document Type"}
		json_file.write_text(json.dumps(json_content))

		# Mock get_app_path to point to our temp dir
		with patch("translation_hub.tasks.get_app_path", return_value=str(app_dir)):
			# Mock frappe.get_app_path("frappe", "..") to return temp_dir parent equivalent
			# so relpath calculation works.
			# Actually, extract_custom_messages uses os.path.relpath(file, frappe.get_app_path("frappe", ".."))
			# We can just check the msgid content, ignoring the path for now

			messages = extract_custom_messages(app_name)

			# Should find 1 message
			self.assertEqual(len(messages), 1)
			# Format: (path, msgid, context, line)
			self.assertEqual(messages[0][1], "Test Dashboard Label")
			self.assertEqual(messages[0][2], "Number Card")

	# --- 3. Test Reuse Existing Translations ---
	def test_reuse_existing_translations(self):
		"""
		Verifies that Orchestrator calls DatabaseTranslationHandler.export_to_po
		when use_database_storage is True.
		"""
		# Mock dependencies
		mock_config = MagicMock(spec=TranslationConfig)
		mock_config.use_database_storage = True
		mock_config.language_code = "pt_BR"
		mock_config.po_file = Path("/tmp/test.po")

		mock_file_handler = MagicMock()
		mock_service = MagicMock()
		mock_logger = MagicMock()

		orchestrator = TranslationOrchestrator(
			config=mock_config, file_handler=mock_file_handler, service=mock_service, logger=mock_logger
		)

		# Patch source of DatabaseTranslationHandler
		with patch("translation_hub.core.database_translation.DatabaseTranslationHandler") as MockDBHandler:
			# Reduce run loop to avoid batch processing logic if possible,
			# or just ensure get_untranslated_entries returns empty to exit early
			mock_file_handler.get_untranslated_entries.return_value = []

			orchestrator.run()

			# Verify DB Handler was initialized
			MockDBHandler.assert_called_with("pt_BR", mock_logger)

			# Verify export_to_po was called
			MockDBHandler.return_value.export_to_po.assert_called_with(str(mock_config.po_file))

			# Verify file_handler.reload() was called
			mock_file_handler.reload.assert_called_once()

	def test_no_reuse_if_storage_disabled(self):
		"""
		Verifies that Orchestrator DOES NOT call database logic if disabled.
		"""
		# Mock dependencies
		mock_config = MagicMock(spec=TranslationConfig)
		mock_config.use_database_storage = False
		# ...
		mock_file_handler = MagicMock()
		mock_service = MagicMock()
		mock_logger = MagicMock()

		orchestrator = TranslationOrchestrator(
			config=mock_config, file_handler=mock_file_handler, service=mock_service, logger=mock_logger
		)

		# Patch source of DatabaseTranslationHandler
		with patch("translation_hub.core.database_translation.DatabaseTranslationHandler") as MockDBHandler:
			mock_file_handler.get_untranslated_entries.return_value = []

			orchestrator.run()

			# Verify DB Handler was NOT called
			MockDBHandler.assert_not_called()
			# Verify reload was NOT called (it's inside the if block)
			mock_file_handler.reload.assert_not_called()
