# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt


import os
from pathlib import Path

import frappe
from frappe import get_app_path
from frappe.model.document import Document

from translation_hub.core.config import TranslationConfig
from translation_hub.core.orchestrator import TranslationOrchestrator
from translation_hub.core.translation_file import TranslationFile
from translation_hub.core.translation_service import GeminiService
from translation_hub.utils.doctype_logger import DocTypeLogger

SYSTEM_PROMPT = """You are an expert software localizer specializing in the Frappe Framework.
Your mission is to translate user interface strings, messages, and content with high precision.

Core Principles:
- **Accuracy**: Convey the exact meaning of the source text.
- **Consistency**: Adhere to standard software terminology.
- **Safety**: Strictly preserve all Jinja/Python variables (e.g., `{{ name }}`, `{0}`, `%s`) and HTML tags.
- **Neutrality**: Maintain a professional and neutral tone unless specified otherwise by the Language Guide.

Follow the specific instructions provided in the App Guide and Language Guide below."""


@frappe.whitelist()
def execute_translation_job(job_name):
	job = frappe.get_doc("Translation Job", job_name)
	logger = DocTypeLogger(job)
	try:
		job.status = "In Progress"
		job.start_time = frappe.utils.now_datetime()
		job.save(ignore_permissions=True)
		frappe.db.commit()

		settings = frappe.get_single("Translator Settings")

		app_path = get_app_path(job.source_app)

		# Ensure POT file exists (auto-generate if missing)
		ensure_pot_file(job.source_app)

		po_path = Path(app_path) / "locale" / f"{job.target_language}.po"
		pot_path = Path(app_path) / "locale" / "main.pot"

		# Get unmasked API key
		api_key = settings.get_password("api_key")

		# 1. Global Guide (System Prompt)
		guides = [f"Global Guide (System Prompt):\n{SYSTEM_PROMPT}"]

		# 2. App-Specific Guide (from Monitored App)
		# Find the monitored app row that matches source_app and target_language (or is generic)
		for app_row in settings.monitored_apps:
			if app_row.source_app == job.source_app and (
				not app_row.target_language or app_row.target_language == job.target_language
			):
				if app_row.standardization_guide:
					guides.append(f"App-Specific Guide ({job.source_app}):\n{app_row.standardization_guide}")
				break

		# 3. Language-Specific Guide (from Translator Language)
		for lang_row in settings.default_languages:
			if lang_row.language_code == job.target_language:
				if lang_row.standardization_guide:
					guides.append(
						f"Language-Specific Guide ({job.target_language}):\n{lang_row.standardization_guide}"
					)
				break

		# Combine all guides
		standardization_guide = "\n\n".join(guides)

		config = TranslationConfig(
			api_key=api_key,
			standardization_guide=standardization_guide,
			logger=logger,
			po_file=po_path,
			pot_file=pot_path,
			use_database_storage=settings.use_database_storage,
			save_to_po_file=settings.save_to_po_file,
			export_po_on_complete=settings.export_po_on_complete,
		)

		file_handler = TranslationFile(po_path=config.po_file, pot_path=config.pot_file, logger=logger)
		file_handler.merge()  # Ensure PO is up-to-date with POT

		# Use MockTranslationService for testing if API key is a placeholder
		if api_key and api_key.startswith("test-"):
			from translation_hub.core.translation_service import MockTranslationService

			logger.info("Using MockTranslationService (test mode)")
			service = MockTranslationService(config=config, logger=logger)
		else:
			logger.info("Using GeminiService (production mode)")
			service = GeminiService(config=config, app_name=job.source_app, logger=logger)

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
		# Determine target languages - NOW ALWAYS ALL ENABLED DEFAULT LANGUAGES
		target_languages = []
		for lang in settings.default_languages:
			if lang.enabled:
				target_languages.append(lang.language_code)

		# Ensure POT file exists (auto-generate if missing)
		ensure_pot_file(monitored_app.source_app)

		for target_language in target_languages:
			app_path = get_app_path(monitored_app.source_app)
			po_path = Path(app_path) / "locale" / f"{target_language}.po"
			pot_path = Path(app_path) / "locale" / "main.pot"

			# Check for untranslated strings
			file_handler = TranslationFile(po_path=po_path, pot_path=pot_path)

			# Merge POT into PO to ensure we have the latest strings
			file_handler.merge()

			untranslated_entries = file_handler.get_untranslated_entries()

			if not untranslated_entries:
				continue

			# Check for active jobs
			active_job = frappe.db.exists(
				"Translation Job",
				{
					"source_app": monitored_app.source_app,
					"target_language": target_language,
					"status": ["in", ["Pending", "Queued", "In Progress"]],
				},
			)

			if active_job:
				continue

			# Create and enqueue a new job
			job = frappe.new_doc("Translation Job")
			job.title = f"Automated: {monitored_app.source_app} - {target_language} - {frappe.utils.now()}"
			job.source_app = monitored_app.source_app
			job.target_language = target_language
			job.insert(ignore_permissions=True)
			job.enqueue_job()


def ensure_pot_file(app_name):
	"""
	Ensures that the main.pot file exists for the given app.
	If not, it generates it by extracting messages from the app.
	"""
	import polib
	from frappe.translate import get_messages_for_app

	app_path = get_app_path(app_name)
	locale_dir = os.path.join(app_path, "locale")
	pot_path = os.path.join(locale_dir, "main.pot")

	if os.path.exists(pot_path):
		return

	if not os.path.exists(locale_dir):
		os.makedirs(locale_dir)

	messages = get_messages_for_app(app_name)
	pot = polib.POFile()
	pot.metadata = {
		"Project-Id-Version": app_name,
		"Report-Msgid-Bugs-To": "",
		"POT-Creation-Date": frappe.utils.now(),
		"PO-Revision-Date": frappe.utils.now(),
		"Last-Translator": "Translation Hub <ai@translationhub.com>",
		"Language-Team": "",
		"MIME-Version": "1.0",
		"Content-Type": "text/plain; charset=UTF-8",
		"Content-Transfer-Encoding": "8bit",
	}

	seen = set()
	for m in messages:
		# m is (path, msgid, context, line) or (path, msgid, context) or (path, msgid)
		if len(m) == 4:
			path, msgid, context, line = m
		elif len(m) == 3:
			path, msgid, context = m
			line = 0
		else:
			path, msgid = m
			context = None
			line = 0

		if not msgid:
			continue

		key = (msgid, context)
		if key in seen:
			continue
		seen.add(key)

		entry = polib.POEntry(msgid=msgid, msgctxt=context, occurrences=[(path, str(line))] if path else [])
		pot.append(entry)

	pot.save(pot_path)
