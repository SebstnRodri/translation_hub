# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class TranslatorSettings(Document):
	def validate(self):
		self.remove_duplicates()
		self.validate_quality_threshold()

	def validate_quality_threshold(self):
		"""Validate that quality_threshold is between 0.0 and 1.0."""
		if hasattr(self, "quality_threshold") and self.quality_threshold is not None:
			if self.quality_threshold < 0.0 or self.quality_threshold > 1.0:
				frappe.throw(
					frappe._(
						"Quality Threshold must be between 0.0 and 1.0. "
						"Got {0}. Did you mean {1}?"
					).format(self.quality_threshold, self.quality_threshold / 10 if self.quality_threshold <= 10 else 0.8),
					frappe.ValidationError,
				)

	def _validate_selects(self):
		"""
		Override to skip validation for dynamic model fields.
		Standard Frappe validation enforces options to be present in the DocType definition.
		"""
		if frappe.flags.in_import:
			return

		# Fields to skip validation for because options are fetched dynamically
		dynamic_fields = ["gemini_model", "groq_model", "openrouter_model"]

		for df in self.meta.get_select_fields():
			if df.fieldname in dynamic_fields:
				continue

			if df.fieldname == "naming_series" or not self.get(df.fieldname) or not df.options:
				continue

			options = (df.options or "").split("\n")

			# if only empty options
			if not filter(None, options):
				continue

			# strip and set
			self.set(df.fieldname, frappe.utils.cstr(self.get(df.fieldname)).strip())
			value = self.get(df.fieldname)

			if value not in options and not (frappe.in_test and value.startswith("_T-")):
				# show an elaborate message
				prefix = frappe._("Row #{0}:").format(self.idx) if self.get("parentfield") else ""
				label = frappe._(self.meta.get_label(df.fieldname))
				comma_options = '", "'.join(frappe._(each) for each in options)

				frappe.throw(
					frappe._('{0} {1} cannot be "{2}". It should be one of "{3}"').format(
						prefix, label, value, comma_options
					)
				)

	def remove_duplicates(self):
		# Remove duplicate Monitored Apps
		unique_apps = set()
		unique_app_rows = []
		if self.monitored_apps:
			for row in self.monitored_apps:
				if row.source_app not in unique_apps:
					unique_apps.add(row.source_app)
					unique_app_rows.append(row)
			self.monitored_apps = unique_app_rows

		# Remove duplicate Default Languages
		unique_langs = set()
		unique_lang_rows = []
		if self.default_languages:
			for row in self.default_languages:
				if row.language_code not in unique_langs:
					unique_langs.add(row.language_code)
					unique_lang_rows.append(row)
			self.default_languages = unique_lang_rows

	def on_update(self):
		self.sync_languages()
		# Trigger automated translations if enabled
		if self.enable_automated_translation:
			frappe.enqueue("translation_hub.tasks.run_automated_translations", queue="long")

	def sync_languages(self):
		if not self.default_languages:
			return

		for lang in self.default_languages:
			if not lang.enabled:
				continue

			if not frappe.db.exists("Language", lang.language_code):
				doc = frappe.new_doc("Language")
				doc.language_code = lang.language_code
				doc.language_name = lang.language_name
				doc.enabled = 1
				doc.insert(ignore_permissions=True)
			else:
				doc = frappe.get_doc("Language", lang.language_code)
				if not doc.enabled:
					doc.enabled = 1
					doc.save(ignore_permissions=True)


@frappe.whitelist()
def test_api_connection():
	"""
	Tests the API connection for the selected LLM provider.
	Returns a success message or error details.
	"""
	frappe.only_for("System Manager")
	settings = frappe.get_single("Translator Settings")
	llm_provider = settings.llm_provider or "Gemini"

	try:
		if llm_provider == "Gemini":
			api_key = settings.get_password("api_key")
			if not api_key:
				return {"success": False, "message": "Gemini API key is not configured."}

			import google.generativeai as genai

			genai.configure(api_key=api_key)
			model = genai.GenerativeModel("gemini-2.0-flash")
			response = model.generate_content("Say 'Connection successful!' in one line.")
			return {
				"success": True,
				"message": f"✅ Gemini connected! Response: {response.text.strip()[:100]}",
			}

		elif llm_provider == "Groq":
			api_key = settings.get_password("groq_api_key")
			if not api_key:
				return {"success": False, "message": "Groq API key is not configured."}

			from openai import OpenAI

			client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
			model_name = settings.groq_model or "llama-3.3-70b-versatile"

			response = client.chat.completions.create(
				model=model_name,
				messages=[{"role": "user", "content": "Say 'Connection successful!' in one line."}],
				max_tokens=50,
			)
			return {
				"success": True,
				"message": f"✅ Groq connected! Model: {model_name}. Response: {response.choices[0].message.content.strip()[:100]}",
			}

		elif llm_provider == "OpenRouter":
			api_key = settings.get_password("openrouter_api_key")
			if not api_key:
				return {"success": False, "message": "OpenRouter API key is not configured."}

			from openai import OpenAI

			client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
			model_name = settings.openrouter_model or "deepseek/deepseek-chat-v3-0324:free"

			response = client.chat.completions.create(
				model=model_name,
				messages=[{"role": "user", "content": "Say 'Connection successful!' in one line."}],
				max_tokens=50,
			)
			return {
				"success": True,
				"message": f"✅ OpenRouter connected! Model: {model_name}. Response: {response.choices[0].message.content.strip()[:100]}",
			}

		else:
			return {"success": False, "message": f"Unknown LLM provider: {llm_provider}"}

	except Exception:
		frappe.log_error(f"Connection failed for {llm_provider}", "Translation Hub Connection Test")
		return {"success": False, "message": "❌ Connection failed. Check Error Log for details."}


@frappe.whitelist()
def fetch_available_models(provider=None):
	"""
	Fetches available models from the selected LLM provider's API.
	Returns a list of model options for the dropdown.
	"""
	frappe.only_for("System Manager")
	settings = frappe.get_single("Translator Settings")
	llm_provider = provider or settings.llm_provider or "Gemini"

	try:
		if llm_provider == "Gemini":
			api_key = settings.get_password("api_key")
			if not api_key:
				return []

			import google.generativeai as genai

			genai.configure(api_key=api_key)
			models = []
			for model in genai.list_models():
				# Filter to only include models that support generateContent
				if "generateContent" in model.supported_generation_methods:
					models.append(
						{
							"value": model.name.replace("models/", ""),
							"label": f"{model.display_name} ({model.name.replace('models/', '')})",
						}
					)
			return sorted(models, key=lambda x: x["label"])

		elif llm_provider == "Groq":
			api_key = settings.get_password("groq_api_key")
			if not api_key:
				return []

			from openai import OpenAI

			client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
			response = client.models.list()

			models = []
			for model in response.data:
				models.append(
					{
						"value": model.id,
						"label": model.id,
					}
				)
			return sorted(models, key=lambda x: x["label"])

		elif llm_provider == "OpenRouter":
			api_key = settings.get_password("openrouter_api_key")
			if not api_key:
				return []

			import requests

			headers = {"Authorization": f"Bearer {api_key}"}
			response = requests.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=30)
			response.raise_for_status()
			data = response.json()

			models = []
			for model in data.get("data", []):
				model_id = model.get("id", "")
				# Highlight free models
				is_free = ":free" in model_id
				label = f"🆓 {model_id}" if is_free else model_id
				models.append(
					{
						"value": model_id,
						"label": label,
					}
				)
			# Sort with free models first
			return sorted(models, key=lambda x: (0 if "🆓" in x["label"] else 1, x["label"]))

		else:
			return []

	except Exception:
		frappe.log_error(f"Failed to fetch models for {llm_provider}", "Translation Hub Model Fetch Error")
		return []


def sync_po_files_to_languages():
	"""
	Scans frappe/locale directory for .po files and creates Language records
	for any that don't exist in the database.
	"""
	import glob
	import os

	# Language name mapping for better display
	LANGUAGE_NAMES = {
		"pt-BR": "Português (Brasil)",
		"pt": "Português",
		"es": "Español",
		"es-AR": "Español (Argentina)",
		"es-BO": "Español (Bolivia)",
		"es-CL": "Español (Chile)",
		"es-CO": "Español (Colombia)",
		"es-MX": "Español (México)",
		"es-PE": "Español (Perú)",
		"en": "English",
		"en-US": "English (United States)",
		"en-GB": "English (United Kingdom)",
		"fr": "Français",
		"fr-CA": "Français (Canada)",
		"de": "Deutsch",
		"it": "Italiano",
		"ja": "日本語",
		"ko": "한국어",
		"zh": "中文",
		"zh-TW": "繁體中文",
		"zh-CN": "简体中文",
		"ru": "Русский",
		"ar": "العربية",
		"hi": "हिन्दी",
		"nl": "Nederlands",
		"pl": "Polski",
		"tr": "Türkçe",
		"vi": "Tiếng Việt",
		"th": "ไทย",
		"sv": "Svenska",
		"da": "Dansk",
		"no": "Norsk",
		"fi": "Suomi",
		"cs": "Čeština",
		"hu": "Magyar",
		"ro": "Română",
		"id": "Bahasa Indonesia",
		"ms": "Bahasa Melayu",
		"uk": "Українська",
		"el": "Ελληνικά",
		"he": "עברית",
		"fa": "فارسی",
		"bn": "বাংলা",
		"ta": "தமிழ்",
		"te": "తెలుగు",
	}

	# Find all .po files in frappe locale directory
	frappe_path = frappe.get_app_path("frappe")
	locale_path = os.path.join(frappe_path, "locale")
	po_files = glob.glob(os.path.join(locale_path, "*.po"))

	created_count = 0
	for po_file in po_files:
		# Extract language code from filename (e.g., pt_BR.po -> pt-BR)
		filename = os.path.basename(po_file)
		lang_code = filename.replace(".po", "").replace("_", "-")

		# Skip if already exists
		if frappe.db.exists("Language", lang_code):
			continue

		# Get proper language name from mapping or generate one
		if lang_code in LANGUAGE_NAMES:
			lang_name = LANGUAGE_NAMES[lang_code]
		elif "-" in lang_code:
			# Fallback: try to make it readable
			base_lang = lang_code.split("-")[0]
			region = lang_code.split("-")[1]
			base_name = LANGUAGE_NAMES.get(base_lang, base_lang.capitalize())
			lang_name = f"{base_name} ({region.upper()})"
		else:
			lang_name = LANGUAGE_NAMES.get(lang_code, lang_code.capitalize())

		# Create Language record
		try:
			doc = frappe.new_doc("Language")
			doc.language_code = lang_code
			doc.language_name = lang_name
			doc.enabled = 0  # Default to disabled
			doc.insert(ignore_permissions=True)
			created_count += 1
			frappe.logger().info(f"Created Language record for {lang_code} ({lang_name}) from .po file")
		except Exception as e:
			frappe.logger().error(f"Failed to create Language for {lang_code}: {e!s}")

	return created_count


@frappe.whitelist()
def populate_language_manager_table():
	"""
	Populates the Language Manager table with all available languages from the Language DocType.
	First syncs .po files to ensure all languages with translation files are included.
	Returns updated table data.
	"""
	frappe.only_for("System Manager")

	# Sync .po files to Languages first
	created = sync_po_files_to_languages()

	settings = frappe.get_single("Translator Settings")

	# Clear existing table
	settings.language_manager_table = []

	# Get all languages sorted by name
	languages = frappe.get_all(
		"Language", fields=["name", "language_name", "enabled"], order_by="language_name asc"
	)

	# Populate table
	for lang in languages:
		settings.append(
			"language_manager_table",
			{"language_code": lang.name, "language_name": lang.language_name, "enabled": lang.enabled or 0},
		)

	# Save without triggering on_update hooks
	settings.flags.ignore_validate = True
	settings.save(ignore_permissions=True)

	msg = f"Loaded {len(languages)} languages into Language Manager"
	if created > 0:
		msg += f" ({created} new language(s) created from .po files)"
	frappe.msgprint(msg)
	return settings.language_manager_table


@frappe.whitelist()
def save_language_manager_settings():
	"""
	Saves the enabled/disabled status of languages from the Language Manager table
	back to the Language DocType.
	"""
	frappe.only_for("System Manager")
	settings = frappe.get_single("Translator Settings")

	if not settings.language_manager_table:
		frappe.throw("Language Manager table is empty. Click 'Load All Languages' first.")

	updated_count = 0
	for row in settings.language_manager_table:
		if frappe.db.exists("Language", row.language_code):
			lang = frappe.get_doc("Language", row.language_code)
			if lang.enabled != row.enabled:
				lang.enabled = row.enabled
				lang.save(ignore_permissions=True)
				updated_count += 1

	frappe.msgprint(f"✅ Language settings saved! {updated_count} language(s) updated.")


@frappe.whitelist()
def cleanup_locale_directories(apps=None):
	"""
	Removes .po files of disabled languages from monitored app locale directories.
	Only keeps files for enabled languages.
	"""
	import glob
	import os
	from pathlib import Path

	frappe.only_for("System Manager")

	if isinstance(apps, str) and apps:
		apps = frappe.parse_json(apps)

	# Get enabled language codes in .po format (pt_BR)
	enabled_langs = frappe.get_all("Language", filters={"enabled": 1}, fields=["name"])
	enabled_codes = {lang.name.replace("-", "_") for lang in enabled_langs}

	settings = frappe.get_single("Translator Settings")

	if not settings.monitored_apps:
		frappe.msgprint("No monitored apps configured.")
		return

	deleted_count = 0
	apps_affected = []

	for app_row in settings.monitored_apps:
		app_name = app_row.source_app

		# Filter by selected apps if provided
		if apps and app_name not in apps:
			continue

		try:
			app_path = frappe.get_app_path(app_name)
			locale_dir = Path(app_path) / "locale"

			if not locale_dir.exists():
				continue

			app_deleted = 0
			# Remove .po files of disabled languages
			for po_file in locale_dir.glob("*.po"):
				if po_file.name.endswith("_test.po"):
					continue

				# Extract lang code from filename (e.g., pt_BR.po -> pt_BR)
				lang_code = po_file.stem

				# Delete if language is NOT enabled
				if lang_code not in enabled_codes:
					po_file.unlink()
					deleted_count += 1
					app_deleted += 1
					frappe.logger().info(f"Deleted {po_file.name} from {app_name}")

			if app_deleted > 0:
				apps_affected.append(f"{app_name} ({app_deleted} files)")

		except Exception as e:
			frappe.log_error(f"Failed to cleanup locale directory for {app_name}: {e}", "Locale Cleanup")

	if deleted_count > 0:
		msg = f"✅ Cleanup completed! Removed {deleted_count} disabled language file(s).<br>"
		msg += f"Apps affected: {', '.join(apps_affected)}"
		frappe.msgprint(msg)
	else:
		frappe.msgprint("No disabled language files found to remove.")
