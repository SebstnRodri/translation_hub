from pathlib import Path

import frappe
import polib


def import_po_to_db(app, language):
	"""
	Import translations from .po file to database.

	IMPORTANT: We intentionally ignore msgctxt (context) because the Frappe frontend
	calls __("text") WITHOUT context, so translations with context are not found.
	By storing translations without context, they work everywhere.
	"""
	print(f"Importing {app} ({language})...")
	app_path = frappe.get_app_path(app)
	po_file = Path(app_path) / "locale" / f"{language.replace('-', '_')}.po"

	if not po_file.exists():
		print(f"File not found: {po_file}")
		return

	po = polib.pofile(str(po_file))
	count = 0
	skipped = 0
	updated = 0

	for entry in po:
		if not entry.msgid or not entry.msgstr:
			continue

		# Check if translation already exists (WITHOUT context)
		existing = frappe.db.get_value(
			"Translation",
			{"source_text": entry.msgid, "language": language, "context": ["in", ["", None]]},
			["name", "translated_text"],
			as_dict=True,
		)

		if existing:
			# Update if translation changed
			if existing.translated_text != entry.msgstr:
				frappe.db.set_value("Translation", existing.name, "translated_text", entry.msgstr)
				updated += 1
			else:
				skipped += 1
		else:
			# Create new translation WITHOUT context
			doc = frappe.get_doc(
				{
					"doctype": "Translation",
					"source_text": entry.msgid,
					"translated_text": entry.msgstr,
					"language": language,
					"context": "",  # Explicitly empty - ensures frontend finds it
					"contributed": 0,
				}
			)
			doc.insert(ignore_permissions=True)
			count += 1
			if count % 100 == 0:
				print(f"Imported {count}...")
				frappe.db.commit()

	frappe.db.commit()

	# Clear translation cache
	frappe.cache.delete_value(["lang_user_translations", "merged_translations"])

	print(f"Done. Created: {count}, Updated: {updated}, Skipped: {skipped}")


def import_all(apps=None, languages=None):
	"""
	Import translations for all apps and enabled languages.

	Args:
		apps: List of apps to import, defaults to all installed apps
		languages: List of languages to import, defaults to all enabled languages
	"""
	from pathlib import Path

	apps_to_import = apps or frappe.get_installed_apps()

	# Get enabled languages
	if languages:
		enabled_languages = languages
	else:
		enabled_languages = frappe.get_all("Language", filters={"enabled": 1}, pluck="name")

	print(f"Apps: {apps_to_import}")
	print(f"Languages: {enabled_languages}")

	for app in apps_to_import:
		for lang in enabled_languages:
			# Check if .po file exists
			app_path = frappe.get_app_path(app)
			lang_code = lang.replace("-", "_")
			po_file = Path(app_path) / "locale" / f"{lang_code}.po"

			if po_file.exists():
				import_po_to_db(app, lang)


def execute():
	"""Legacy function - imports all apps for all enabled languages."""
	import_all()
