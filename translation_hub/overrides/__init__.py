"""
Translation Hub Overrides for Frappe Desk Translations

This package contains monkey patches to fix missing translation calls in Frappe.
Patches are applied at import time when Frappe is on version-16-beta branch.
"""

import subprocess


def get_frappe_branch():
	"""Get the current Git branch of Frappe app."""
	try:
		import frappe

		result = subprocess.check_output(
			["git", "rev-parse", "--abbrev-ref", "HEAD"],
			cwd=frappe.get_app_path("frappe"),
			stderr=subprocess.DEVNULL,
		)
		return result.decode().strip()
	except Exception:
		return None


def apply_patches(bootinfo=None):
	"""
	Apply monkey patches for Frappe desk translations.
	Called via boot_session hook (receives bootinfo argument).

	Note: Patches are applied at module import time, this function
	just ensures patches stay applied across reloads.
	"""
	_ensure_patches_applied()


def _ensure_patches_applied():
	"""Apply patches if not already applied."""
	import frappe
	import frappe.boot

	# Check if already patched by looking for our marker
	if getattr(frappe.boot.load_desktop_data, "_translation_hub_patched", False):
		return

	branch = get_frappe_branch()

	# Only apply patches on version-16-beta (fix/desk-translations already has fixes)
	if branch != "version-16-beta":
		return

	from translation_hub.overrides import boot_patches, desktop_icon_patches

	boot_patches.apply()
	desktop_icon_patches.apply()

	# Mark as patched
	frappe.boot.load_desktop_data._translation_hub_patched = True

	try:
		frappe.logger("translation_hub").info("Desk translation patches applied successfully")
	except Exception:
		pass  # Logger might not be ready yet


# Apply patches immediately when this module is imported
try:
	_ensure_patches_applied()
except Exception:
	pass  # Frappe might not be fully initialized yet
