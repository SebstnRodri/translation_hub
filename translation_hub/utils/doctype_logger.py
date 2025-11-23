# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class DocTypeLogger:
	def __init__(self, doc: Document):
		self.doc = doc

	def info(self, message):
		self._log(message, "Info")

	def warning(self, message):
		self._log(message, "Warning")

	def error(self, message):
		self._log(message, "Error")

	def debug(self, message):
		# For now, we will not log debug messages to the doctype
		pass

	def _log(self, message, level):
		if not self.doc.log:
			self.doc.log = ""
		self.doc.log += f"[{level}] {message}\n"
		self.doc.save(ignore_permissions=True)
		frappe.db.commit()

	def update_progress(self, translated, total):
		self.doc.translated_strings = translated
		self.doc.total_strings = total
		self.doc.save(ignore_permissions=True)
		frappe.db.commit()
