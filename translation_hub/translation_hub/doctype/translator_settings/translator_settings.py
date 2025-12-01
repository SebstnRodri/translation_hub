# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class TranslatorSettings(Document):
	def validate(self):
		self.remove_duplicates()

	def remove_duplicates(self):
		# Remove duplicate Monitored Apps
		unique_apps = set()
		unique_app_rows = []
		if self.monitored_apps:
			for row in self.monitored_apps:
				if row.source_app not in unique_apps:
					unique_apps.add(row.source_app)
					unique_app_rows.append(row)
			self.monitored_apps = unique_app_rows

		# Remove duplicate Default Languages
		unique_langs = set()
		unique_lang_rows = []
		if self.default_languages:
			for row in self.default_languages:
				if row.language_code not in unique_langs:
					unique_langs.add(row.language_code)
					unique_lang_rows.append(row)
			self.default_languages = unique_lang_rows

	def on_update(self):
		self.sync_languages()
		# Trigger automated translations if enabled
		if self.enable_automated_translation:
			frappe.enqueue("translation_hub.tasks.run_automated_translations", queue="long")

	def sync_languages(self):
		if not self.default_languages:
			return

		for lang in self.default_languages:
			if not lang.enabled:
				continue

			if not frappe.db.exists("Language", lang.language_code):
				doc = frappe.new_doc("Language")
				doc.language_code = lang.language_code
				doc.language_name = lang.language_name
				doc.enabled = 1
				doc.insert(ignore_permissions=True)
			else:
				doc = frappe.get_doc("Language", lang.language_code)
				if not doc.enabled:
					doc.enabled = 1
					doc.save(ignore_permissions=True)
