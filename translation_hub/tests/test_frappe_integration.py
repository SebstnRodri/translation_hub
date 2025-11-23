# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt


import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestFrappeIntegration(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Translation Job", {"title": "Test Job"})
		frappe.db.delete("Translation Job", {"source_app": "frappe", "target_language": "es"})
		frappe.db.delete("Translation Job", {"source_app": "frappe", "target_language": "fr"})

		if not frappe.db.exists("App", "frappe"):
			frappe.get_doc({"doctype": "App", "app_name": "frappe", "app_title": "Frappe Framework"}).insert(
				ignore_permissions=True
			)

		self.job = frappe.get_doc(
			{
				"doctype": "Translation Job",
				"title": "Test Job",
				"source_app": "frappe",
				"target_language": "es",
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		self.job.delete(ignore_permissions=True)

	@patch("frappe.enqueue")
	def test_enqueue_job(self, mock_enqueue):
		self.job.enqueue_job()
		self.assertEqual(self.job.status, "Queued")
		mock_enqueue.assert_called_with(
			"translation_hub.tasks.execute_translation_job",
			job_name=self.job.name,
			is_async=True,
		)

	@patch("translation_hub.tasks.TranslationOrchestrator")
	def test_execute_translation_job(self, mock_orchestrator):
		from translation_hub.tasks import execute_translation_job

		settings = frappe.get_single("Translator Settings")
		settings.api_key = "test_api_key"
		settings.save(ignore_permissions=True)

		execute_translation_job(self.job.name)

		self.job.reload()
		self.assertEqual(self.job.status, "Completed")
		mock_orchestrator.assert_called_once()
		mock_orchestrator.return_value.run.assert_called_once()

		settings.delete(ignore_permissions=True)

	@patch("translation_hub.tasks.TranslationFile")
	@patch("frappe.enqueue")
	def test_run_automated_translations(self, mock_enqueue, mock_file):
		from translation_hub.tasks import run_automated_translations

		mock_file.return_value.get_untranslated_entries.return_value = [{"msgid": "test"}]

		settings = frappe.get_single("Translator Settings")
		settings.enable_automated_translation = 1
		settings.append("monitored_apps", {"source_app": "frappe", "target_language": "fr"})
		settings.save(ignore_permissions=True)

		run_automated_translations()

		self.assertEqual(mock_enqueue.call_count, 1)

		settings.delete(ignore_permissions=True)
