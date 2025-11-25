# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt


import os

import frappe
from frappe import get_app_path
from frappe.model.document import Document

from translation_hub.core.config import TranslationConfig
from translation_hub.core.orchestrator import TranslationOrchestrator
from translation_hub.core.translation_file import TranslationFile
from translation_hub.core.translation_service import GeminiService
from translation_hub.utils.doctype_logger import DocTypeLogger


@frappe.whitelist()
def execute_translation_job(job_name):
	job = frappe.get_doc("Translation Job", job_name)
	try:
		job.status = "In Progress"
		job.start_time = frappe.utils.now_datetime()
		job.save(ignore_permissions=True)
		frappe.db.commit()

		logger = DocTypeLogger(job)
		settings = frappe.get_single("Translator Settings")

		app_path = get_app_path(job.source_app)
		po_path = os.path.join(app_path, "locale", f"{job.target_language}.po")
		pot_path = os.path.join(app_path, "locale", "main.pot")

		# Get unmasked API key
		api_key = settings.get_password("api_key")

		config = TranslationConfig(
			api_key=api_key,
			standardization_guide=settings.standardization_guide,
			logger=logger,
			po_file=po_path,
			pot_file=pot_path,
			use_database_storage=settings.use_database_storage,
			save_to_po_file=settings.save_to_po_file,
			export_po_on_complete=settings.export_po_on_complete,
		)

		file_handler = TranslationFile(po_path=config.po_file, pot_path=config.pot_file, logger=logger)

		# Use MockTranslationService for testing if API key is a placeholder
		logger.info(f"Checking API Key for Mock Service: '{api_key}'")
		if api_key and api_key.startswith("test-"):
			from translation_hub.core.translation_service import MockTranslationService
			logger.info("Using MockTranslationService (test mode)")
			service = MockTranslationService(config=config, logger=logger)
		else:
			logger.info("Using GeminiService (production mode)")
			service = GeminiService(config=config, logger=logger)

		orchestrator = TranslationOrchestrator(
			config=config, file_handler=file_handler, service=service, logger=logger
		)

		orchestrator.run()

		job.status = "Completed"
		job.end_time = frappe.utils.now_datetime()
		job.save(ignore_permissions=True)
		frappe.db.commit()

	except Exception as e:
		if job:
			logger.error(f"Job failed: {e}")
			job.status = "Failed"
			job.end_time = frappe.utils.now_datetime()
			job.save(ignore_permissions=True)
			frappe.db.commit()
		frappe.log_error(frappe.get_traceback(), "Translation Job Failed")


def run_automated_translations():
	settings = frappe.get_single("Translator Settings")
	if not settings.enable_automated_translation:
		return

	for monitored_app in settings.monitored_apps:
		app_path = get_app_path(monitored_app.source_app)
		po_path = os.path.join(app_path, "translations", f"{monitored_app.target_language}.po")
		pot_path = os.path.join(app_path, "translations", f"{monitored_app.source_app}.pot")

		# Check for untranslated strings
		file_handler = TranslationFile(po_path=po_path, pot_path=pot_path)
		untranslated_entries = file_handler.get_untranslated_entries()

		if not untranslated_entries:
			continue

		# Check for active jobs
		active_job = frappe.db.exists(
			"Translation Job",
			{
				"source_app": monitored_app.source_app,
				"target_language": monitored_app.target_language,
				"status": ["in", ["Pending", "Queued", "In Progress"]],
			},
		)

		if active_job:
			continue

		# Create and enqueue a new job
		job = frappe.new_doc("Translation Job")
		job.title = f"Automated: {monitored_app.source_app} - {monitored_app.target_language}"
		job.source_app = monitored_app.source_app
		job.target_language = monitored_app.target_language
		job.insert(ignore_permissions=True)
		job.enqueue_job()
