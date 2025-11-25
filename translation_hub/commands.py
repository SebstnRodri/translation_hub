import click
import frappe
from frappe.commands import pass_context

@click.command("setup-languages")
@pass_context
def setup_languages(context):
	"""Enable languages defined in Translator Settings."""
	site = context.sites[0]
	frappe.init(site=site)
	frappe.connect()

	try:
		settings = frappe.get_single("Translator Settings")
		if not settings.default_languages:
			click.echo("No languages defined in Translator Settings. Please configure them first.")
			return

		settings.sync_languages()
		
		# Feedback is now implicit, but we can iterate to show what happened if needed,
		# or just say "Languages synced successfully."
		click.echo("Languages synced based on Translator Settings.")
		
		frappe.db.commit()
	finally:
		frappe.destroy()

commands = [
	setup_languages
]
