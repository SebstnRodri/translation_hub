# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class TranslationJob(Document):
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
			job_name=self.name,
			is_async=True,
		)
		self.status = "Queued"
		self.save(ignore_permissions=True)
		frappe.db.commit()
		return self.status
