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
def execute_translation_job(translation_job_name):
	job = frappe.get_doc("Translation Job", translation_job_name)
	logger = DocTypeLogger(job)
	try:
		job.status = "In Progress"
		job.start_time = frappe.utils.now_datetime()
		job.save(ignore_permissions=True)
		frappe.db.commit()

		settings = frappe.get_single("Translator Settings")

		# Sync remote translations if configured
		if getattr(settings, "sync_before_translate", False) and settings.backup_repo_url:
			try:
				from translation_hub.core.git_sync_service import GitSyncService

				git_service = GitSyncService(settings)
				if git_service.sync():
					logger.info("Synced remote translations before translating.")
			except Exception as e:
				logger.warning(f"Failed to sync remote translations: {e}")

		app_path = get_app_path(job.source_app)

		# Ensure POT file exists (auto-generate if missing)
		ensure_pot_file(job.source_app)

		po_path = Path(app_path) / "locale" / f"{job.target_language.replace('-', '_')}.po"
		pot_path = Path(app_path) / "locale" / "main.pot"

		# Get unmasked API key
		api_key = settings.get_password("api_key")

		# 1. Global Guide (System Prompt)
		guides = [f"Global Guide (System Prompt):\n{SYSTEM_PROMPT}"]

		# 2. App-Specific Guide (from Monitored App)
		# Find the monitored app row that matches source_app and target_language (or is generic)
		for app_row in settings.monitored_apps:
			if app_row.source_app == job.source_app:
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

		# 4. App Glossary (App + Language)
		# Find App Glossary for this App and Language
		app_glossary_name = frappe.db.exists(
			"App Glossary", {"app": job.source_app, "language": job.target_language}
		)
		if app_glossary_name:
			app_glossary = frappe.get_doc("App Glossary", app_glossary_name)
			if app_glossary.glossary_items:
				glossary_text = "Glossary Terms:\n"
				for item in app_glossary.glossary_items:
					term_line = f"- {item.term}: {item.translation}"
					if item.description:
						term_line += f" ({item.description})"
					glossary_text += term_line + "\n"
				guides.append(glossary_text)

		# Combine all guides
		standardization_guide = "\n\n".join(guides)

		# Determine which API key to use based on LLM provider
		llm_provider = getattr(settings, "llm_provider", "Gemini")

		if llm_provider == "Groq":
			active_api_key = settings.get_password("groq_api_key")
		elif llm_provider == "OpenRouter":
			active_api_key = settings.get_password("openrouter_api_key")
		else:
			active_api_key = api_key  # Gemini API key

		# Detect Test Mode based on the active provider's API key
		is_test_mode = active_api_key and active_api_key.startswith("test-")
		if is_test_mode:
			logger.info("TEST MODE DETECTED: Disabling database storage and redirecting PO output.")
			# Isolate test output
			po_path = Path(app_path) / "locale" / f"{job.target_language.replace('-', '_')}_test.po"
			settings.use_database_storage = False
			settings.save_to_po_file = True  # Force save to file so we can verify output
			settings.export_po_on_complete = False

		config = TranslationConfig(
			api_key=active_api_key,
			standardization_guide=standardization_guide,
			logger=logger,
			po_file=po_path,
			pot_file=pot_path,
			use_database_storage=settings.use_database_storage,
			save_to_po_file=settings.save_to_po_file,
			export_po_on_complete=settings.export_po_on_complete,
			language_code=job.target_language,
		)

		file_handler = TranslationFile(po_path=config.po_file, pot_path=config.pot_file, logger=logger)
		file_handler.merge()  # Ensure PO is up-to-date with POT

		# Use MockTranslationService for testing if API key is a placeholder
		if is_test_mode:
			from translation_hub.core.translation_service import MockTranslationService

			logger.info("Using MockTranslationService (test mode)")
			service = MockTranslationService(config=config, logger=logger)
		else:
			# Select service based on LLM provider setting
			if llm_provider == "Groq":
				from translation_hub.core.translation_service import GroqService

				if not active_api_key:
					raise ValueError("Groq API key is not configured in Translator Settings.")

				groq_model = getattr(settings, "groq_model", None) or "llama-3.3-70b-versatile"
				config.model_name = groq_model

				logger.info(f"Using GroqService (model: {groq_model})")
				service = GroqService(config=config, app_name=job.source_app, logger=logger)
			elif llm_provider == "OpenRouter":
				from translation_hub.core.translation_service import OpenRouterService

				if not active_api_key:
					raise ValueError("OpenRouter API key is not configured in Translator Settings.")

				openrouter_model = (
					getattr(settings, "openrouter_model", None) or "deepseek/deepseek-chat-v3-0324:free"
				)
				config.model_name = openrouter_model

				logger.info(f"Using OpenRouterService (model: {openrouter_model})")
				service = OpenRouterService(config=config, app_name=job.source_app, logger=logger)
			else:
				# Default to Gemini
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
			po_path = Path(app_path) / "locale" / f"{target_language.replace('-', '_')}.po"
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
	Generates or regenerates the main.pot file for the given app.
	Always extracts fresh messages to ensure new strings are included.
	"""
	import polib
	from frappe.translate import get_messages_for_app

	app_path = get_app_path(app_name)
	locale_dir = os.path.join(app_path, "locale")
	pot_path = os.path.join(locale_dir, "main.pot")

	# Always regenerate to capture new strings (important for development)

	if not os.path.exists(locale_dir):
		os.makedirs(locale_dir)

	messages = get_messages_for_app(app_name)
	pot = polib.POFile()
	now_str = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M")
	pot.metadata = {
		"Project-Id-Version": "1.0",
		"Report-Msgid-Bugs-To": "",
		"POT-Creation-Date": now_str,
		"PO-Revision-Date": now_str,
		"Last-Translator": "Translation Hub <ai@translationhub.com>",
		"Language-Team": "",
		"MIME-Version": "1.0",
		"Content-Type": "text/plain; charset=utf-8",
		"Content-Transfer-Encoding": "8bit",
		"X-Generator": "Frappe Translation Hub",
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


@frappe.whitelist()
def backup_translations():
	"""
	Backs up translations to the configured Git repository.
	"""
	from translation_hub.core.git_sync_service import GitSyncService

	settings = frappe.get_single("Translator Settings")
	if not settings.backup_repo_url:
		frappe.throw("Backup Repository URL is not configured in Translator Settings.")

	service = GitSyncService(settings)
	service.backup()


@frappe.whitelist()
def restore_translations():
	"""
	Restores translations from the configured Git repository.
	"""
	from translation_hub.core.git_sync_service import GitSyncService

	settings = frappe.get_single("Translator Settings")
	if not settings.backup_repo_url:
		frappe.throw("Backup Repository URL is not configured in Translator Settings.")

	service = GitSyncService(settings)
	service.restore()
