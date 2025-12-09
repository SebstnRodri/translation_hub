# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class TranslationJob(Document):
	def validate(self):
		self.validate_configuration()
		self.validate_duplication()

	def validate_duplication(self):
		"""Prevent multiple active jobs for the same App and Language."""
		if self.status in ["Completed", "Failed", "Cancelled"]:
			return

		existing_job = frappe.db.exists(
			"Translation Job",
			{
				"source_app": self.source_app,
				"target_language": self.target_language,
				"status": ["in", ["Pending", "Queued", "In Progress"]],
				"name": ["!=", self.name],
			},
		)

		if existing_job:
			frappe.throw(
				f"An active Translation Job ({existing_job}) already exists for {self.source_app} ({self.target_language}). "
				"Please wait for it to complete.",
				frappe.ValidationError,
			)

	def validate_configuration(self):
		"""Ensure this job corresponds to a valid configuration in Translator Settings."""
		settings = frappe.get_single("Translator Settings")
		# 1. Check if App is monitored
		is_app_monitored = False
		for app in settings.monitored_apps:
			if app.source_app == self.source_app:
				is_app_monitored = True
				break

		if not is_app_monitored:
			frappe.throw(
				f"App '{self.source_app}' is not configured for monitoring. Please add it to Translator Settings.",
				frappe.ValidationError,
			)

		# 2. Check if Language is enabled
		is_language_enabled = False
		for lang in settings.default_languages:
			if lang.language_code == self.target_language and lang.enabled:
				is_language_enabled = True
				break

		if not is_language_enabled:
			frappe.throw(
				f"Language '{self.target_language}' is not enabled in Translator Settings.",
				frappe.ValidationError,
			)

	def before_save(self):
		total = self.total_strings or 0
		translated = self.translated_strings or 0

		if total > 0:
			self.progress_percentage = (translated / total) * 100
		else:
			self.progress_percentage = 0

	@frappe.whitelist()
	def enqueue_job(self):
		frappe.enqueue(
			"translation_hub.tasks.execute_translation_job",
			queue="long",
			job_name=self.name,
			translation_job_name=self.name,
			is_async=True,
		)
		self.status = "Queued"
		self.save(ignore_permissions=True)
		frappe.db.commit()
		return self.status


@frappe.whitelist()
def check_existing_translations(source_app, target_language):
	"""
	Check for existing translations in PO file and database.
	Returns counts and warnings for UI validation before save.
	"""
	frappe.only_for("System Manager")
	import os

	import polib
	from frappe import get_app_path

	result = {
		"po_file_count": 0,
		"database_count": 0,
		"total_in_pot": 0,
		"has_existing": False,
		"message": "",
	}

	try:
		app_path = get_app_path(source_app)
		locale_dir = os.path.join(app_path, "locale")
		
		# Normalize language code for file path (pt-BR -> pt_BR)
		file_lang_code = target_language.replace("-", "_")
		po_path = os.path.join(locale_dir, f"{file_lang_code}.po")
		pot_path = os.path.join(locale_dir, "main.pot")

		# Count entries in POT file
		if os.path.exists(pot_path):
			pot = polib.pofile(pot_path)
			result["total_in_pot"] = len([e for e in pot if not e.obsolete])

		# Count translated entries in PO file
		if os.path.exists(po_path):
			po = polib.pofile(po_path)
			translated = [e for e in po if e.translated() and not e.obsolete]
			result["po_file_count"] = len(translated)

		# Count translations in database
		# First try exact match, then try with underscore
		db_count = frappe.db.count("Translation", {"language": target_language})
		if db_count == 0:
			db_count = frappe.db.count("Translation", {"language": file_lang_code})
		result["database_count"] = db_count

		# Determine if there are existing translations
		total_existing = result["po_file_count"] + result["database_count"]
		result["has_existing"] = total_existing > 0

		if result["has_existing"]:
			parts = []
			if result["po_file_count"] > 0:
				parts.append(f"{result['po_file_count']} in .po file")
			if result["database_count"] > 0:
				parts.append(f"{result['database_count']} in database")
			
			result["message"] = (
				f"⚠️ Translations already exist for {source_app} ({target_language}):\n"
				f"{', '.join(parts)}.\n\n"
				f"Continue? Only untranslated strings will be processed."
			)

	except Exception as e:
		result["message"] = f"Error checking translations: {e}"

	return result
