# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class TranslatorSettings(Document):
	def validate(self):
		self.remove_duplicates()

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
