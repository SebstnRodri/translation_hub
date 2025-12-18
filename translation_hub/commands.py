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


@click.command("maintenance")
@click.option("--fix-jobs", is_flag=True, help="Cancel stuck translation jobs")
@click.option("--fix-langs", is_flag=True, help="Fix language code issues")
@click.option("--clear-cache", is_flag=True, help="Clear translation caches")
@click.option("--all", "run_all", is_flag=True, help="Run all maintenance tasks")
@pass_context
def maintenance(context, fix_jobs, fix_langs, clear_cache, run_all):
	"""Run translation maintenance tasks to fix common issues."""
	site = context.sites[0]
	frappe.init(site=site)
	frappe.connect()

	try:
		from translation_hub.core.maintenance import TranslationMaintenance

		m = TranslationMaintenance()

		if run_all or not any([fix_jobs, fix_langs, clear_cache]):
			m.run_all()
		else:
			if fix_jobs:
				m.fix_stuck_jobs()
			if fix_langs:
				m.fix_language_codes()
			if clear_cache:
				m.clear_caches()

		frappe.db.commit()
	finally:
		frappe.destroy()


commands = [setup_languages, maintenance]
