"""
Translation Hub Maintenance Module

Provides utilities to diagnose and fix common translation issues:
- Stuck translation jobs
- Translation cache not loading
- Language code mismatches
"""

from datetime import timedelta

import frappe
from frappe.utils import now_datetime


class TranslationMaintenance:
	"""
	Smart maintenance utilities for Translation Hub.
	"""

	def __init__(self, verbose: bool = True):
		self.verbose = verbose
		self.issues_found = []
		self.fixes_applied = []

	def log(self, message: str):
		if self.verbose:
			print(message)

	def run_all(self) -> dict:
		"""Run all maintenance checks and fixes."""
		self.log("=" * 60)
		self.log("🔧 Translation Hub Maintenance")
		self.log("=" * 60)

		# 1. Check and fix stuck jobs
		self.fix_stuck_jobs()

		# 2. Check and fix language code issues
		self.fix_language_codes()

		# 3. Clear translation caches
		self.clear_caches()

		# 4. Verify translations loading
		self.verify_translations()

		# Summary
		self.log("\n" + "=" * 60)
		self.log("📊 Summary:")
		self.log(f"   Issues found: {len(self.issues_found)}")
		self.log(f"   Fixes applied: {len(self.fixes_applied)}")
		self.log("=" * 60)

		return {
			"issues_found": self.issues_found,
			"fixes_applied": self.fixes_applied,
		}

	def fix_stuck_jobs(self, hours_threshold: int = 2):
		"""
		Detect and cancel translation jobs stuck for too long.
		Jobs in 'Queued' or 'In Progress' for more than X hours are cancelled.
		"""
		self.log("\n🔍 Checking for stuck jobs...")

		threshold_time = now_datetime() - timedelta(hours=hours_threshold)

		stuck_jobs = frappe.get_all(
			"Translation Job",
			filters={
				"status": ["in", ["Queued", "In Progress"]],
				"creation": ["<", threshold_time],
			},
			fields=["name", "status", "source_app", "target_language", "creation"],
		)

		if not stuck_jobs:
			self.log("   ✅ No stuck jobs found.")
			return

		self.log(f"   ⚠️  Found {len(stuck_jobs)} stuck job(s):")

		for job in stuck_jobs:
			self.log(f"      - {job.name} ({job.status})")
			self.issues_found.append(f"Stuck job: {job.name}")

			# Cancel the stuck job
			frappe.db.set_value(
				"Translation Job",
				job.name,
				"status",
				"Cancelled",
				update_modified=True,
			)
			self.fixes_applied.append(f"Cancelled: {job.name}")
			self.log("         → Cancelled ✓")

		frappe.db.commit()

	def fix_language_codes(self):
		"""
		Detect and report language code mismatches.
		Frappe uses 'pt-BR' (hyphen), but some imports might use 'pt_BR' (underscore).
		"""
		self.log("\n🔍 Checking language codes...")

		# Get all language codes in Translation table
		langs = frappe.db.sql("SELECT DISTINCT language FROM tabTranslation", as_dict=True)
		lang_codes = [l.language for l in langs]
		self.log(f"   Languages in database: {lang_codes}")

		# Check for underscore variants that should be hyphen
		for lang in lang_codes:
			if "_" in lang:
				correct_code = lang.replace("_", "-")
				self.issues_found.append(f"Language code with underscore: {lang}")
				self.log(f"   ⚠️  '{lang}' should be '{correct_code}'")

				# Check if correct code already exists
				existing = frappe.db.count("Translation", {"language": correct_code})
				if existing > 0:
					self.log(f"      → '{correct_code}' already exists with {existing} translations")
					# Could merge, but that's risky - just report
				else:
					# Fix the language code
					frappe.db.sql(
						"UPDATE tabTranslation SET language = %s WHERE language = %s", (correct_code, lang)
					)
					frappe.db.commit()
					self.fixes_applied.append(f"Fixed language code: {lang} -> {correct_code}")
					self.log(f"      → Fixed to '{correct_code}' ✓")

		# Check system language setting
		sys_lang = frappe.db.get_single_value("System Settings", "language")
		self.log(f"   System Settings.language: {sys_lang}")

		# Check site_config
		site_lang = frappe.conf.get("language", "not set")
		self.log(f"   site_config.language: {site_lang}")

		if sys_lang == "en" and site_lang != "en":
			self.log(f"   ⚠️  System Settings still set to 'en', updating to '{site_lang}'...")
			frappe.db.set_single_value("System Settings", "language", site_lang)
			frappe.db.commit()
			self.fixes_applied.append(f"Updated System Settings.language to {site_lang}")
			self.log(f"      → Updated to '{site_lang}' ✓")

	def clear_caches(self):
		"""Clear all translation-related caches."""
		self.log("\n🔍 Clearing translation caches...")

		# Clear translation cache keys
		cache_keys = [
			"lang_user_translations",
			"merged_translations",
			"translation_assets",
		]

		for key in cache_keys:
			frappe.cache.delete_value(key)

		# Clear boot cache which includes translations
		frappe.cache.delete_key("bootinfo")

		# Clear all language-specific translation caches
		# Get all languages from database dynamically
		langs = frappe.get_all("Language", pluck="name")
		for lang in langs:
			frappe.cache.delete_value(f"lang_{lang}")
			frappe.cache.delete_value(f"translation_{lang}")
			# Also clear underscore variant if exists
			lang_underscore = lang.replace("-", "_")
			if lang_underscore != lang:
				frappe.cache.delete_value(f"lang_{lang_underscore}")
				frappe.cache.delete_value(f"translation_{lang_underscore}")

		self.fixes_applied.append("Cleared translation caches")
		self.log("   ✅ Caches cleared.")

	def verify_translations(self):
		"""Verify that translations are loading correctly."""
		self.log("\n🔍 Verifying translation loading...")

		# Get user's language
		user_lang = frappe.db.get_value("User", frappe.session.user, "language") or "en"
		self.log(f"   User language: {user_lang}")

		# Check a known translation
		test_source = "Settings"
		db_translation = frappe.db.get_value(
			"Translation", {"source_text": test_source, "language": user_lang}, "translated_text"
		)

		if db_translation:
			self.log(f"   '{test_source}' in database: '{db_translation}'")

			# Test the __ function
			from frappe.translate import get_user_translations

			user_trans = get_user_translations(user_lang)

			if test_source in user_trans:
				self.log(f"   '{test_source}' in cache: '{user_trans[test_source]}' ✓")
			else:
				self.log(f"   ⚠️  '{test_source}' not found in cache!")
				self.issues_found.append(f"Translation not in cache: {test_source}")
		else:
			self.log(f"   '{test_source}' not in database for {user_lang}")

		# Count translations
		db_count = frappe.db.count("Translation", {"language": user_lang})
		self.log(f"   Total translations in database for {user_lang}: {db_count}")


# Convenience functions for CLI
def run_maintenance():
	"""Run all maintenance tasks. Call via bench execute."""
	m = TranslationMaintenance()
	return m.run_all()


def cancel_stuck_jobs(hours: int = 2):
	"""Cancel stuck jobs older than X hours."""
	m = TranslationMaintenance()
	m.fix_stuck_jobs(hours)
	frappe.db.commit()


def fix_language_codes():
	"""Fix language code issues."""
	m = TranslationMaintenance()
	m.fix_language_codes()
	frappe.db.commit()


def clear_translation_cache():
	"""Clear all translation caches."""
	m = TranslationMaintenance()
	m.clear_caches()
