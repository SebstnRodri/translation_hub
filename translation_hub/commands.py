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


@click.command("compile-ecosystem-translations")
@click.option("--locale", default="pt_BR", help="Target locale to compile (e.g. pt_BR)")
@click.option("--apps", default=None, help="Comma-separated list of apps (default: all supported apps)")
@click.option("--force", is_flag=True, default=True, help="Force recompilation even if MO file is newer")
@click.option(
	"--clear-cache", is_flag=True, default=False, help="Clear translation cache in Redis after compiling"
)
@pass_context
def compile_ecosystem_translations(context, locale, apps, force, clear_cache):
	"""Compile gettext PO files into MO binaries in sites/assets/locale for all ecosystem apps."""
	site = context.sites[0] if context.sites else None
	if site:
		frappe.init(site=site)
		frappe.connect()

	try:
		from translation_hub.core.locale_compiler import LocaleCompiler

		apps_list = [a.strip() for a in apps.split(",") if a.strip()] if apps else None
		compiler = LocaleCompiler()
		report = compiler.compile_ecosystem(apps=apps_list, locale=locale, force=force)

		click.secho(f"\nTranslation Compilation Report [{locale}]:", fg="cyan", bold=True)
		for item in report.compiled:
			click.secho(f"  ✓ {item.app:<20} -> {item.mo_path} ({item.size_bytes} bytes)", fg="green")
		for item in report.skipped:
			click.secho(f"  - {item.app:<20} (skipped: {item.reason})", fg="yellow")
		for item in report.errors:
			click.secho(f"  ✗ {item.app:<20} ERROR: {item.error}", fg="red", bold=True)

		click.echo(
			f"\nSummary: {report.total_compiled} compiled, "
			f"{report.total_skipped} skipped, {report.total_errors} errors."
		)

		if clear_cache:
			cleared = compiler.invalidate_cache(site_name=site)
			click.secho(f"✓ Cache cleared for sites: {', '.join(cleared)}", fg="green")

	finally:
		if site:
			frappe.destroy()


@click.command("invalidate-translation-cache")
@click.option("--all-sites", is_flag=True, default=False, help="Invalidate cache across all sites in bench")
@pass_context
def invalidate_translation_cache_cmd(context, all_sites):
	"""Invalidate translation cache in Redis (merged_translations & bootinfo)."""
	site = context.sites[0] if (context.sites and not all_sites) else None
	from translation_hub.core.locale_compiler import invalidate_translation_cache

	cleared = invalidate_translation_cache(site_name=site if not all_sites else None)
	click.secho(
		f"✓ Translation cache cleared for: {', '.join(cleared) if cleared else 'no sites'}", fg="green"
	)


commands = [
	setup_languages,
	maintenance,
	compile_ecosystem_translations,
	invalidate_translation_cache_cmd,
]
