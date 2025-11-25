# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class TranslatorSettings(Document):
	def on_update(self):
		self.sync_languages()

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
