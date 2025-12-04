import frappe


def clean_mock_translations():
	"""
	Deletes translations from the database that start with mock prefixes like [ES], [PT-BR], [MOCK].
	"""
	mock_prefixes = ["[ES]", "[PT-BR]", "[MOCK]"]
	total_deleted = 0

	for prefix in mock_prefixes:
		translations = frappe.get_all(
			"Translation", filters={"translated_text": ["like", f"{prefix}%"]}, pluck="name"
		)

		if translations:
			count = len(translations)
			print(f"Found {count} translations with prefix '{prefix}'. Deleting...")

			for name in translations:
				frappe.delete_doc("Translation", name, ignore_permissions=True)

			total_deleted += count

	frappe.db.commit()
	print(f"Cleanup complete. Total deleted: {total_deleted}")
