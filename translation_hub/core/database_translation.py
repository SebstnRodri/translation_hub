"""
Database Translation Handler

Stores and retrieves translations using Frappe's Translation DocType.
Translations stored here automatically render in the app because Frappe
loads them via get_user_translations() which has highest priority.
"""

import logging
from typing import Any

import frappe


class DatabaseTranslationHandler:
	"""
	Store and retrieve translations using Frappe's Translation DocType.

	Translations stored here automatically render in the app because
	Frappe loads them via get_user_translations() which has highest priority.
	"""

	def __init__(self, language: str, logger: logging.Logger | None = None):
		"""
		Initialize handler for a specific language.

		Args:
			language: Language code (e.g., 'es', 'pt_BR')
			logger: Optional logger instance
		"""
		self.language = language
		self.logger = logger or logging.getLogger(__name__)

	def save_translations(self, entries: list[dict[str, Any]]) -> int:
		"""
		Save multiple translations to database.

		Args:
			entries: List of dicts with 'msgid', 'msgstr', optional 'context'

		Returns:
			Number of translations saved
		"""
		saved_count = 0

		for entry in entries:
			msgid = entry.get("msgid")
			msgstr = entry.get("msgstr")
			context = entry.get("context", "")

			if not msgid or not msgstr:
				continue

			# Skip failed translations
			if msgstr.startswith("[TRANSLATION_FAILED]"):
				self.logger.warning(f"Skipping failed translation: {msgid}")
				continue

			try:
				self._save_single(msgid, msgstr, context)
				saved_count += 1
			except Exception as e:
				self.logger.error(f"Failed to save translation for '{msgid}': {e}")

		# Clear translation cache so changes apply immediately
		self._clear_cache()

		self.logger.info(f"Saved {saved_count}/{len(entries)} translations to database")
		return saved_count

	def _save_single(self, msgid: str, msgstr: str, context: str = ""):
		"""
		Save or update a single translation.

		Args:
			msgid: Source text (original string)
			msgstr: Translated text
			context: Optional context for the translation
		"""
		filters = {"source_text": msgid, "language": self.language, "context": context}

		existing = frappe.db.get_value("Translation", filters, "name")

		if existing:
			# Update existing translation
			frappe.db.set_value("Translation", existing, "translated_text", msgstr)
			self.logger.debug(f"Updated: {msgid}")
		else:
			# Create new translation
			doc = frappe.get_doc(
				{
					"doctype": "Translation",
					"language": self.language,
					"source_text": msgid,
					"translated_text": msgstr,
					"context": context,
				}
			)
			doc.insert(ignore_permissions=True)
			self.logger.debug(f"Created: {msgid}")

	def get_all_translations(self) -> list[dict]:
		"""
		Get all translations for this language from database.

		Returns:
			List of dicts with 'source_text', 'translated_text', 'context'
		"""
		return frappe.get_all(
			"Translation",
			filters={"language": self.language},
			fields=["source_text", "translated_text", "context"],
		)

	def _clear_cache(self):
		"""Clear translation cache so changes apply immediately."""
		from frappe.translate import clear_cache

		clear_cache()
		self.logger.debug("Translation cache cleared")

	def export_to_po(self, po_path: str):
		"""
		Export database translations to .po file.
		Optional - only needed for external tools or version control.

		Args:
			po_path: Path to save the .po file
		"""
		import os

		import polib

		if os.path.exists(po_path):
			self.logger.info(f"Loading existing PO file for export: {po_path}")
			po = polib.pofile(po_path, encoding="utf-8")
		else:
			self.logger.info(f"Creating new PO file for export: {po_path}")
			po = polib.POFile()
			po.metadata = {
				"Project-Id-Version": "1.0",
				"Language": self.language,
				"MIME-Version": "1.0",
				"Content-Type": "text/plain; charset=utf-8",
			}

		translations = self.get_all_translations()
		updated_count = 0

		for t in translations:
			msgid = t["source_text"]
			msgstr = t["translated_text"]
			context = t.get("context")

			entry = po.find(msgid, msgctxt=context)
			if entry:
				if entry.msgstr != msgstr:
					entry.msgstr = msgstr
					if "fuzzy" in entry.flags:
						entry.flags.remove("fuzzy")
					updated_count += 1
			else:
				# Only add new entry if it doesn't exist (less common for export, usually we update)
				# But if we are creating a new file, we add everything.
				entry = polib.POEntry(msgid=msgid, msgstr=msgstr)
				if context:
					entry.msgctxt = context
				po.append(entry)
				updated_count += 1

		po.save(po_path)
		self.logger.info(f"Exported/Updated {updated_count} translations to {po_path}")
