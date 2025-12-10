from pathlib import Path

import frappe
import polib


def import_po_to_db(app, language):
	print(f"Importing {app} ({language})...")
	app_path = frappe.get_app_path(app)
	po_file = Path(app_path) / "locale" / f"{language.replace('-', '_')}.po"

	if not po_file.exists():
		print(f"File not found: {po_file}")
		return

	po = polib.pofile(str(po_file))
	count = 0

	for entry in po:
		if not entry.msgid or not entry.msgstr:
			continue

		# Check existence
		exists = frappe.db.exists("Translation", {"source_text": entry.msgid, "language": language})

		if not exists:
			doc = frappe.get_doc(
				{
					"doctype": "Translation",
					"source_text": entry.msgid,
					"translated_text": entry.msgstr,
					"language": language,
					"contributed": 0,  # Legacy import
				}
			)
			doc.insert(ignore_permissions=True)
			count += 1
			if count % 100 == 0:
				print(f"Imported {count}...")
				frappe.db.commit()

	frappe.db.commit()
	print(f"Done. Imported {count} new translations.")


def execute():
	import_po_to_db("erpnext", "pt-BR")
