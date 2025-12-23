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
from translation_hub.utils.localization import get_localization_profile


@frappe.whitelist()
def execute_translation_job(translation_job_name):
	frappe.only_for("System Manager")
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

		# 1. Global Guide (System Prompt)
		# Load from settings, fallback to a sensible default if somehow empty
		system_prompt = settings.system_prompt or "You are an expert translator."
		guides = [f"Global Guide (System Prompt):\n{system_prompt}"]

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
			# Gemini (default)
			active_api_key = settings.get_password("api_key")

		# Detect Test Mode based on the active provider's API key
		is_test_mode = active_api_key and active_api_key.startswith("test-")
		if is_test_mode:
			logger.info("TEST MODE DETECTED: Disabling database storage and redirecting PO output.")
			# Isolate test output
			po_path = Path(app_path) / "locale" / f"{job.target_language.replace('-', '_')}_test.po"
			settings.use_database_storage = False
			settings.save_to_po_file = True  # Force save to file so we can verify output
			settings.export_po_on_complete = False

		# Auto-detect localization profile if not set
		if not job.localization_profile:
			# Try to find active profile for this language, scoped by app
			# Note: target_language is the name/code of the Language document
			profile = get_localization_profile(job.target_language, job.source_app)
			if profile:
				job.localization_profile = profile
				job.save(ignore_permissions=True)
				frappe.db.commit()
				logger.info(f"Auto-detected Localization Profile: {profile}")

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
			localization_profile=job.localization_profile,
			# Agent Pipeline configuration
			use_agent_pipeline=getattr(settings, "use_agent_pipeline", False),
			quality_threshold=getattr(settings, "quality_threshold", 0.8),
			regional_expert_profile=getattr(job, "regional_expert_profile", None)
			or getattr(settings, "default_regional_expert", None),
			llm_provider=llm_provider,
		)
		config.app_name = job.source_app  # Set app_name for agent context

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
				gemini_model = getattr(settings, "gemini_model", None) or "gemini-2.0-flash"
				config.model_name = gemini_model

				logger.info(f"Using GeminiService (model: {gemini_model})")
				service = GeminiService(config=config, app_name=job.source_app, logger=logger)

		orchestrator = TranslationOrchestrator(
			config=config, file_handler=file_handler, service=service, logger=logger
		)

		orchestrator.run()

		# Compile translations to .mo files for immediate use
		logger.info(f"Compiling translations for {job.source_app}...")
		from frappe.gettext.translate import compile_translations

		compile_translations(job.source_app)
		logger.info(f"✓ Compiled translations for {job.source_app}")

		# Automatic backup if configured
		if settings.backup_repo_url and getattr(settings, "backup_frequency", None) != "None":
			try:
				logger.info("Initiating automatic backup to remote repository...")
				from translation_hub.core.git_sync_service import GitSyncService

				git_service = GitSyncService(settings)
				git_service.backup(apps=[job.source_app])
				logger.info("✓ Backup completed successfully")
			except Exception as e:
				logger.warning(f"Backup failed (non-critical): {e}")

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

	# Custom Extraction for Dashboard Cards (Number Card, Workspace)
	custom_messages = extract_custom_messages(app_name)
	if custom_messages:
		messages.extend(custom_messages)

	existing_metadata = {}
	if os.path.exists(pot_path):
		try:
			existing_pot = polib.pofile(pot_path)
			existing_metadata = existing_pot.metadata
		except Exception:
			pass

	pot = polib.POFile()
	now_str = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M")

	creation_date = existing_metadata.get("POT-Creation-Date", now_str)

	pot.metadata = {
		"Project-Id-Version": "1.0",
		"Report-Msgid-Bugs-To": "",
		"POT-Creation-Date": creation_date,
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
@frappe.whitelist()
def backup_translations(apps=None):
	"""
	Backs up translations to the configured Git repository.
	"""
	frappe.only_for("System Manager")
	from translation_hub.core.git_sync_service import GitSyncService

	if isinstance(apps, str) and apps:
		apps = frappe.parse_json(apps)

	settings = frappe.get_single("Translator Settings")
	if not settings.backup_repo_url:
		frappe.throw("Backup Repository URL is not configured in Translator Settings.")

	service = GitSyncService(settings)
	service.backup(apps=apps)


@frappe.whitelist()
def restore_translations(apps=None):
	"""
	Restores translations from the configured Git repository.
	"""
	frappe.only_for("System Manager")
	from translation_hub.core.git_sync_service import GitSyncService

	if isinstance(apps, str) and apps:
		apps = frappe.parse_json(apps)

	settings = frappe.get_single("Translator Settings")
	if not settings.backup_repo_url:
		frappe.throw("Backup Repository URL is not configured in Translator Settings.")

	service = GitSyncService(settings)
	service.restore(apps=apps)


@frappe.whitelist()
def cleanup_locale_directories(apps=None):
	"""
	Removes .po files of disabled languages from monitored app locale directories.
	"""
	frappe.only_for("System Manager")
	from translation_hub.translation_hub.doctype.translator_settings import translator_settings

	translator_settings.cleanup_locale_directories(apps=apps)


def extract_custom_messages(app_name):
	"""
	Scans the app directory for dashboard artifacts (Number Card, Workspace)
	that behave like standard doctypes but are not automatically picked up.
	"""
	import json
	import os
	from glob import glob

	app_path = get_app_path(app_name)
	messages = []

	# Define artifacts to scan: (Folder Name, Field to Extract, Context)
	artifacts = [
		("number_card", "label", "Number Card"),
		("workspace", "label", "Workspace"),
		("dashboard_chart", "chart_name", "Dashboard Chart"),
	]

	for folder, field, context in artifacts:
		# Search pattern: app/module/doctype_folder/doc_name/doc_name.json
		# We'll just recursively look for json files in relevant folders
		# A broader search might be safer:
		search_path = os.path.join(app_path, "**", folder, "**", "*.json")
		files = glob(search_path, recursive=True)

		for file_path in files:
			if not file_path.endswith(".json"):
				continue

			try:
				with open(file_path) as f:
					data = json.load(f)

				msgid = data.get(field)
				if msgid and isinstance(msgid, str):
					# Format: (path, msgid, context, line)
					# Path should be relative to bench root usually, but get_messages returns relative to app?
					# Actually get_messages returns path relative to bench dir usually
					rel_path = os.path.relpath(file_path, frappe.get_app_path("frappe", ".."))
					messages.append((rel_path, msgid, context, 0))

			except Exception:
				continue

	return messages


def auto_review_pending_tasks():
	"""
	Automatically review pending Translation Tasks.
	
	For tasks with rejection_reason:
	1. Generate a new translation using LLM considering the rejection reason
	2. Evaluate the new translation quality
	3. If passes threshold, auto-approve and save to database
	
	This is scheduled to run hourly via Frappe scheduler.
	"""
	from translation_hub.translation_hub.doctype.translation_task.translation_task import (
		evaluate_translation_quality,
		_save_translation_to_db,
	)
	
	settings = frappe.get_single("Translator Settings")
	threshold = settings.quality_threshold or 0.8
	
	# Get pending tasks that have a rejection reason (user rejected it)
	pending_tasks = frappe.get_all(
		"Translation Task",
		filters={
			"status": ["in", ["Pending", "In Progress"]],
			"rejection_reason": ["is", "set"],  # Only process tasks with rejection reason
		},
		fields=["name", "source_text", "suggested_translation", "rejection_reason", "target_language"],
	)
	
	regenerated_count = 0
	approved_count = 0
	failed_count = 0
	
	for task_data in pending_tasks:
		try:
			# Generate new translation based on rejection reason
			new_translation = _generate_corrected_translation(
				settings,
				task_data.source_text,
				task_data.suggested_translation or "",
				task_data.rejection_reason,
				task_data.target_language
			)
			
			if not new_translation:
				failed_count += 1
				continue
			
			regenerated_count += 1
			
			# Evaluate quality
			result = evaluate_translation_quality(
				task_data.source_text,
				new_translation,
				threshold
			)
			
			# Update task with new translation
			task = frappe.get_doc("Translation Task", task_data.name)
			task.suggested_translation = new_translation
			task.corrected_translation = new_translation
			
			if result["passed"]:
				# Auto-approve
				_save_translation_to_db(task, new_translation)
				task.status = "Completed"
				task.save(ignore_permissions=True)
				approved_count += 1
				
				frappe.logger().info(
					f"Auto-approved task {task_data.name}: score={result['score']:.2f}"
				)
			else:
				# Still needs review - save the new suggestion
				task.save(ignore_permissions=True)
				
				frappe.logger().info(
					f"Regenerated but not approved task {task_data.name}: score={result['score']:.2f}, issues={result['issues']}"
				)
				
		except Exception as e:
			frappe.log_error(f"Auto-review failed for {task_data.name}: {e}", "Translation Auto Review")
			failed_count += 1
	
	frappe.db.commit()
	
	frappe.logger().info(
		f"Auto-review completed: regenerated={regenerated_count}, approved={approved_count}, failed={failed_count}"
	)
	
	return {
		"regenerated": regenerated_count,
		"approved": approved_count,
		"failed": failed_count
	}


def _generate_corrected_translation(settings, source_text: str, previous_translation: str, rejection_reason: str, target_language: str) -> str | None:
	"""
	Generate a corrected translation using LLM based on the rejection reason.
	
	Returns:
		The new translation or None if failed
	"""
	prompt = f"""You are a professional translator specialized in ERP/business software.
You need to CORRECT a translation that was rejected by a human reviewer.

SOURCE TEXT: {source_text}
TARGET LANGUAGE: {target_language}

PREVIOUS TRANSLATION (REJECTED): {previous_translation}

REJECTION REASON FROM REVIEWER: {rejection_reason}

CRITICAL RULES:
1. Keep ALL placeholders EXACTLY as they appear in the source:
   - Empty: {{}} and #{{}} must remain as {{}} and #{{}}
   - Numbered: {{0}}, {{1}}, #{{0}} must NOT be changed
   - DO NOT add numbers to empty placeholders
2. Keep HTML tags intact
3. FIX the specific issue mentioned in the rejection reason
4. Use appropriate business/ERP terminology

Respond with ONLY the corrected translation, nothing else."""

	try:
		llm_provider = settings.llm_provider or "Gemini"
		
		if llm_provider == "Gemini":
			import google.generativeai as genai
			
			api_key = settings.get_password("api_key")
			genai.configure(api_key=api_key)
			model = genai.GenerativeModel(settings.gemini_model or "gemini-2.0-flash")
			response = model.generate_content(prompt)
			return response.text.strip()
			
		elif llm_provider in ("Groq", "OpenRouter"):
			from openai import OpenAI
			
			if llm_provider == "Groq":
				api_key = settings.get_password("groq_api_key")
				base_url = "https://api.groq.com/openai/v1"
				model_name = settings.groq_model or "llama-3.3-70b-versatile"
			else:
				api_key = settings.get_password("openrouter_api_key")
				base_url = "https://openrouter.ai/api/v1"
				model_name = settings.openrouter_model or "deepseek/deepseek-chat-v3-0324:free"
			
			client = OpenAI(api_key=api_key, base_url=base_url)
			response = client.chat.completions.create(
				model=model_name,
				messages=[{"role": "user", "content": prompt}],
				temperature=0.3,
			)
			return response.choices[0].message.content.strip()
		else:
			frappe.logger().warning(f"Unknown LLM provider: {llm_provider}")
			return None
			
	except Exception as e:
		frappe.log_error(f"Translation generation failed: {e}", "Translation Auto Review")
		return None


@frappe.whitelist()
def run_auto_review():
	"""Whitelist wrapper for auto_review_pending_tasks."""
	frappe.only_for("System Manager")
	result = auto_review_pending_tasks()
	frappe.msgprint(
		f"Auto-review completed: regenerated={result['regenerated']}, approved={result['approved']}, failed={result['failed']}",
		title="Auto Review Complete"
	)
	return result
