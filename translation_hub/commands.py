import click
import frappe
from frappe.commands import pass_context

def get_common_languages():
	return [
		{"code": "pt-BR", "name": "Português (Brasil)"},
		{"code": "es-MX", "name": "Español (México)"},
		{"code": "fr-CA", "name": "Français (Canada)"},
	]

@click.command("setup-languages")
@pass_context
def setup_languages(context):
	"""Enable common languages and create missing ones (e.g., pt-BR)."""
	site = context.sites[0]
	frappe.init(site=site)
	frappe.connect()

	try:
		common_languages = get_common_languages()
		
		for lang in common_languages:
			if not frappe.db.exists("Language", lang["code"]):
				doc = frappe.new_doc("Language")
				doc.language_code = lang["code"]
				doc.language_name = lang["name"]
				doc.enabled = 1
				doc.insert(ignore_permissions=True)
				click.echo(f"Created language: {lang['name']} ({lang['code']})")
			else:
				doc = frappe.get_doc("Language", lang["code"])
				if not doc.enabled:
					doc.enabled = 1
					doc.save(ignore_permissions=True)
					click.echo(f"Enabled language: {lang['name']} ({lang['code']})")
				else:
					click.echo(f"Language already enabled: {lang['name']} ({lang['code']})")
		
		# Also enable generic languages if disabled
		generic_langs = ["pt", "es", "fr", "de", "it"]
		for code in generic_langs:
			if frappe.db.exists("Language", code):
				doc = frappe.get_doc("Language", code)
				if not doc.enabled:
					doc.enabled = 1
					doc.save(ignore_permissions=True)
					click.echo(f"Enabled generic language: {code}")

		frappe.db.commit()
	finally:
		frappe.destroy()

commands = [
	setup_languages
]
