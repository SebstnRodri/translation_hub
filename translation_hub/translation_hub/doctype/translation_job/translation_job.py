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
