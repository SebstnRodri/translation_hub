import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

import google.generativeai as genai
from dotenv import load_dotenv

from translation_hub.core.config import TranslationConfig


class TranslationService(ABC):
	"""
	Abstract base class for a translation service.
	Defines the interface that all concrete translation services must implement.
	"""

	@abstractmethod
	def translate(self, entries: list[dict]) -> list[dict]:
		"""
		Translates a list of entries, each containing a msgid and context.

		Args:
		    entries: A list of dictionaries, where each dictionary
		             represents an entry to be translated.

		Returns:
		    A list of dictionaries with the translated strings.
		"""
		pass

	def _fetch_learning_examples(self) -> str:
		"""
		Fetches relevant few-shot learning examples from 'Translation Learning'.
		Includes both Full Corrections and Term-specific Corrections.
		Returns a formatted string of examples or empty string.
		"""
		if not getattr(self, "app_name", None):
			return ""

		try:
			import frappe

			if not self.config or not self.config.language_code:
				return ""

			instruction = ""

			# 1. Fetch Term Corrections (higher priority - specific rules)
			term_corrections = frappe.get_all(
				"Translation Learning",
				filters={"language": self.config.language_code, "learning_type": "Term Correction"},
				fields=["problematic_term", "correct_term"],
				order_by="creation desc",
				limit=10,
			)

			if term_corrections:
				instruction += "\n\n**CRITICAL TERM RULES (Always follow these):**\n"
				instruction += "The following terms are often mistranslated. Use the CORRECT translation:\n"
				for tc in term_corrections:
					if tc.problematic_term and tc.correct_term:
						instruction += f"- '{tc.problematic_term}' → translate as '{tc.correct_term}'\n"

			# 2. Fetch Full Corrections (few-shot examples)
			full_corrections = frappe.get_all(
				"Translation Learning",
				filters={
					"domain": self.app_name,
					"language": self.config.language_code,
					"learning_type": "Full Correction",
				},
				fields=["source_text", "ai_output", "human_correction"],
				order_by="creation desc",
				limit=3,
			)

			if full_corrections:
				instruction += "\n\n**Learning from Corrections (Few-Shot Examples):**\n"
				instruction += "Pay attention to these past corrections. The 'AI Output' was REJECTED. Use the 'Human Correction' style/terminology instead.\n"

				for ex in full_corrections:
					instruction += f"- Source: '{ex.source_text}'\n"
					instruction += f"  ❌ Avoid: '{ex.ai_output}'\n"
					instruction += f"  ✅ Preferred: '{ex.human_correction}'\n"

			return instruction

		except Exception:
			return ""


class MockTranslationService(TranslationService):
	"""
	A mock implementation of TranslationService for testing without API calls.
	Simulates translation by adding a language prefix to the original text.
	"""

	def __init__(self, config: TranslationConfig, logger: logging.Logger | None = None):
		self.config = config
		self.logger = logger or logging.getLogger(__name__)
		self.delay = 0.1  # Simulate API delay (seconds)
		self.fail_rate = 0.0  # Probability of failure (0.0 to 1.0)

	def translate(self, entries: list[dict[str, Any]]) -> list[dict[str, str]]:
		"""
		Mock translation that adds [ES] prefix to simulate Spanish translation.
		"""
		import random

		self.logger.info(f"[MOCK] Translating batch of {len(entries)} entries")
		time.sleep(self.delay * len(entries))  # Simulate processing time

		translations = []
		for entry in entries:
			msgid = entry["msgid"]

			# Simulate occasional failures if fail_rate > 0
			if random.random() < self.fail_rate:
				self.logger.warning(f"[MOCK] Simulated failure for: '{msgid}'")
				# Return None to skip this entry (don't write failed translations)
				translations.append(None)
				continue

			# Simple mock translation: add language prefix
			# Preserve placeholders and HTML tags
			lang_code = self.config.language_code.upper() if self.config.language_code else "MOCK"
			mock_translation = f"[{lang_code}] {msgid}"

			# Preserve whitespace
			preserved = self._preserve_whitespace(msgid, mock_translation)
			translations.append({"msgid": msgid, "msgstr": preserved})

			self.logger.debug(f"[MOCK] '{msgid}' -> '{preserved}'")

		return translations

	@staticmethod
	def _preserve_whitespace(original: str, translated: str) -> str:
		"""Preserve leading and trailing whitespace from original."""
		if not original:
			return translated
		leading_spaces = len(original) - len(original.lstrip(" "))
		trailing_spaces = len(original) - len(original.rstrip(" "))
		return (" " * leading_spaces) + translated.strip() + (" " * trailing_spaces)


class GeminiService(TranslationService):
	"""
	A concrete implementation of TranslationService that uses the Google Gemini API.
	"""

	def __init__(
		self, config: TranslationConfig, app_name: str | None = None, logger: logging.Logger | None = None
	):
		self.config = config
		self.app_name = app_name
		self.logger = logger or logging.getLogger(__name__)
		self.model = self._configure_model()
		self.context = self._fetch_context()

	def _configure_model(self):
		"""
		Configures and returns a Gemini generative model.
		"""
		load_dotenv()
		api_key = self.config.api_key or os.getenv("GEMINI_API_KEY")
		if not api_key:
			raise ValueError("Gemini API key not found.")
		genai.configure(api_key=api_key)
		return genai.GenerativeModel(self.config.model_name)

	def translate(self, entries: list[dict[str, Any]]) -> list[dict[str, str]]:
		"""
		Translates a batch of entries using the Gemini API.
		Includes retry logic and fallback to single-entry translation.
		"""
		# --- BATCH TRANSLATION ATTEMPT ---
		for attempt in range(self.config.max_batch_retries):
			try:
				prompt = self._build_batch_prompt(entries)
				self.logger.debug(f"Batch prompt:\n{prompt}")
				self.logger.info(
					f"  [API Call] Translating batch of {len(entries)} entries via Gemini (Attempt {attempt + 1}/{self.config.max_batch_retries})"
				)

				response = self.model.generate_content(prompt)
				response_text = response.text
				json_str = self._clean_json_response(response_text)
				translated_items = json.loads(json_str)

				if isinstance(translated_items, list) and len(translated_items) == len(entries):
					processed_translations = []
					for i, item in enumerate(translated_items):
						original_msgid = entries[i]["msgid"]
						translated_text = item.get("translated", "")
						preserved_text = self._preserve_whitespace(original_msgid, translated_text)
						processed_translations.append({"msgid": original_msgid, "msgstr": preserved_text})
					return processed_translations

			except (json.JSONDecodeError, Exception) as e:
				self.logger.warning(
					f"  [Warning] Batch translation attempt {attempt + 1}/{self.config.max_batch_retries} failed: {e}"
				)
				if attempt < self.config.max_batch_retries - 1:
					time.sleep(self.config.retry_wait_seconds)

		# --- FALLBACK TO SINGLE-ENTRY TRANSLATION ---
		self.logger.info(
			f"  [Info] Batch failed after {self.config.max_batch_retries} attempts. Switching to single-entry mode for this batch."
		)
		return [self._translate_single(entry) for entry in entries]

	def _translate_single(self, entry: dict[str, Any]) -> dict[str, str] | None:
		"""
		Translates a single entry, with retries.
		"""
		msgid = entry["msgid"]
		for attempt in range(self.config.max_single_retries):
			try:
				prompt = self._build_single_prompt(entry)
				self.logger.debug(f"Single entry prompt:\n{prompt}")
				self.logger.info(
					f"    [API Call] Translating single entry via Gemini: '{msgid}' (Attempt {attempt + 1}/{self.config.max_single_retries})"
				)

				response = self.model.generate_content(prompt)
				response_text = response.text
				json_str = self._clean_json_response(response_text)
				translated_item = json.loads(json_str)
				if isinstance(translated_item, dict) and "translated" in translated_item:
					translated_text = self._preserve_whitespace(msgid, translated_item["translated"])
					return {"msgid": msgid, "msgstr": translated_text}
			except (json.JSONDecodeError, Exception) as e:
				self.logger.warning(
					f"    [Warning] Single-entry attempt {attempt + 1}/{self.config.max_single_retries} failed for '{msgid}': {e}"
				)
				if attempt < self.config.max_single_retries - 1:
					time.sleep(self.config.retry_wait_seconds)

		self.logger.error(
			f"    [Error] Failed to translate '{msgid}' after {self.config.max_single_retries} attempts."
		)
		# Return None to skip this entry (don't write failed translations)
		return None

	def _fetch_context(self) -> dict[str, Any]:
		"""
		Fetches translation context for the app.
		Priority:
		1. App DocType configuration (UI)
		2. 'translation_context' hook (Code)
		3. Default/Empty
		"""
		if not self.app_name:
			return {}

		import frappe

		context = {}

		# 1. Try App DocType
		try:
			if frappe.db.exists("App", self.app_name):
				app_doc = frappe.get_doc("App", self.app_name)

				if app_doc.domain:
					context["domain"] = app_doc.domain
				if app_doc.tone:
					context["tone"] = app_doc.tone
				if app_doc.description:
					context["description"] = app_doc.description

				if app_doc.do_not_translate:
					context["do_not_translate"] = [item.term for item in app_doc.do_not_translate]
		except Exception as e:
			self.logger.warning(f"Failed to fetch context from App DocType: {e}")

		# 2. Try Hook if UI context is empty (or merge? Design said priority, let's merge with UI winning)
		# Actually design said: "If fields are set in the App document, use them."
		# Let's check hooks if we still miss info or just as a fallback for the whole context object?
		# Let's treat UI as overrides.

		try:
			hooks = frappe.get_hooks("translation_context", app_name=self.app_name)
			if hooks:
				# hooks returns a list of python paths string
				for hook in hooks:
					hook_context = frappe.call(hook)
					if isinstance(hook_context, dict):
						# Merge hook context, but UI context (already in 'context') takes precedence
						# So we update hook_context with context, then set context to result
						hook_context.update(context)
						context = hook_context
		except Exception as e:
			self.logger.warning(f"Failed to fetch context from hook: {e}")

		# 3. Localization Profile (Takes precedence over App Context for glossary)
		if getattr(self.config, "localization_profile", None):
			try:
				profile = frappe.get_doc("Localization Profile", self.config.localization_profile)

				# Regional Glossary
				if profile.regional_glossary:
					if "glossary" not in context:
						context["glossary"] = {}

					for item in profile.regional_glossary:
						# Format: "Term": "Translation" (Context)
						term_key = item.english_term
						translation = item.localized_term
						if item.context:
							translation += f" ({item.context})"
						context["glossary"][term_key] = translation

				# Context Rules
				if profile.context_rules:
					if "context_rules" not in context:
						context["context_rules"] = []

					for rule in profile.context_rules:
						context["context_rules"].append(
							{
								"pattern": rule.source_pattern,
								"translation": rule.target_translation,
								"priority": rule.priority,
								"examples": rule.examples,
							}
						)

			except Exception as e:
				self.logger.warning(f"Failed to fetch Localization Profile: {e}")

		return context

	def _fetch_learning_examples(self) -> str:
		"""
		Fetches relevant few-shot learning examples from 'Translation Learning'.
		Returns a formatted string of examples or empty string.
		"""
		if not self.app_name:
			return ""

		try:
			import frappe

			# Fetch learned corrections for this app and language
			# Limit to 3 most recent to avoid context bloat
			examples = frappe.get_all(
				"Translation Learning",
				filters={"domain": self.app_name, "language": self.config.language_code},
				fields=["source_text", "ai_output", "human_correction"],
				order_by="creation desc",
				limit=3,
			)

			if not examples:
				return ""

			instruction = "\n\n**Learning from Corrections (Few-Shot Examples):**\n"
			instruction += "Pay attention to these past corrections. The 'AI Output' was REJECTED. Use the 'Human Correction' style/terminology instead.\n"

			for ex in examples:
				instruction += f"- Source: '{ex.source_text}'\n"
				instruction += f"  ❌ Avoid (AI Bad Output): '{ex.ai_output}'\n"
				instruction += f"  ✅ Preferred (Human): '{ex.human_correction}'\n"

			return instruction

		except Exception as e:
			self.logger.warning(f"Failed to fetch learning examples: {e}")
			return ""

	def _build_batch_prompt(self, entries: list[dict[str, Any]]) -> str:
		base_prompt = (
			f"You are a translator specialized in ERP systems, translating to the language '{self.config.language_code}'.\n"
			"Translate the following texts, considering the context where they appear in the code (occurrences), "
			"developer comments (comment), and other flags (flags).\n"
		)

		if self.context:
			base_prompt += "\n**Application Context:**\n"
			if self.context.get("domain"):
				base_prompt += f"- Domain: {self.context['domain']}\n"
			if self.context.get("tone"):
				base_prompt += f"- Tone of Voice: {self.context['tone']}\n"
			if self.context.get("description"):
				base_prompt += f"- Description: {self.context['description']}\n"

			if self.context.get("glossary"):
				base_prompt += "\n**Glossary (Term -> Translation):**\n"
				for term, trans in self.context["glossary"].items():
					base_prompt += f"- {term}: {trans}\n"

			if self.context.get("do_not_translate"):
				base_prompt += "\n**DO NOT TRANSLATE these terms:**\n"
				base_prompt += ", ".join(self.context["do_not_translate"]) + "\n"

			if self.context.get("context_rules"):
				base_prompt += "\n**CONTEXT RULES (Strictly follow these):**\n"
				for rule in self.context["context_rules"]:
					base_prompt += f"- Pattern: '{rule['pattern']}' → Translate as: '{rule['translation']}'"
					if rule.get("priority", 0) > 80:
						base_prompt += " (CRITICAL)"
					base_prompt += "\n"
					if rule.get("examples"):
						base_prompt += f"  Example: {rule['examples']}\n"

		# Inject Learning Examples
		base_prompt += self._fetch_learning_examples()

		base_prompt += (
			"\nReturn YOUR RESPONSE AS A SINGLE JSON ARRAY of objects, each with the key 'translated'.\n"
			"The output array must have exactly the same number of items as the input.\n"
			"Keep placeholders like `{0}` and HTML tags like `<strong>` intact."
		)

		base_prompt += (
			"\nReturn YOUR RESPONSE AS A SINGLE JSON ARRAY of objects, each with the key 'translated'.\n"
			"The output array must have exactly the same number of items as the input.\n"
			"Keep placeholders like `{0}` and HTML tags like `<strong>` intact."
		)
		if self.config.standardization_guide:
			base_prompt += f"\n\n**Standardization Guide:**\n{self.config.standardization_guide}\nFollow this guide strictly."

		items_to_translate = json.dumps(entries, indent=2, ensure_ascii=False)

		return (
			f"{base_prompt}\n\n"
			"Items to translate:\n"
			f"{items_to_translate}\n\n"
			"Output JSON Array (only the array of 'translated' objects):\n"
		)

	def _build_single_prompt(self, entry: dict[str, Any]) -> str:
		base_prompt = (
			f"You are a translator specialized in ERP systems, translating to the language '{self.config.language_code}'.\n"
			"Translate the text below, considering the context where it appears in the code (occurrences), "
			"developer comments (comment), and other flags (flags).\n"
		)

		if self.context:
			base_prompt += "\n**Application Context:**\n"
			if self.context.get("domain"):
				base_prompt += f"- Domain: {self.context['domain']}\n"
			if self.context.get("tone"):
				base_prompt += f"- Tone of Voice: {self.context['tone']}\n"
			if self.context.get("description"):
				base_prompt += f"- Description: {self.context['description']}\n"

			if self.context.get("glossary"):
				base_prompt += "\n**Glossary (Term -> Translation):**\n"
				for term, trans in self.context["glossary"].items():
					base_prompt += f"- {term}: {trans}\n"

			if self.context.get("do_not_translate"):
				base_prompt += "\n**DO NOT TRANSLATE these terms:**\n"
				base_prompt += ", ".join(self.context["do_not_translate"]) + "\n"

			if self.context.get("context_rules"):
				base_prompt += "\n**CONTEXT RULES (Strictly follow these):**\n"
				for rule in self.context["context_rules"]:
					base_prompt += f"- Pattern: '{rule['pattern']}' → Translate as: '{rule['translation']}'"
					if rule.get("priority", 0) > 80:
						base_prompt += " (CRITICAL)"
					base_prompt += "\n"
					if rule.get("examples"):
						base_prompt += f"  Example: {rule['examples']}\n"

		base_prompt += (
			"\nReturn YOUR RESPONSE AS A SINGLE JSON OBJECT with the key 'translated'.\n"
			"Keep placeholders like `{0}` and HTML tags like `<strong>` intact."
		)
		if self.config.standardization_guide:
			base_prompt += f"\n\n**Standardization Guide:**\n{self.config.standardization_guide}\nFollow this guide strictly."

		item_to_translate = json.dumps(entry, indent=2, ensure_ascii=False)

		return (
			f"{base_prompt}\n\n"
			"Item to translate:\n"
			f"{item_to_translate}\n\n"
			"Output JSON Object (only the 'translated' object):\n"
		)

	@staticmethod
	def _clean_json_response(text: str) -> str:
		cleaned = text.strip()
		if cleaned.startswith("```json"):
			cleaned = cleaned.removeprefix("```json").strip()
		elif cleaned.startswith("```"):
			cleaned = cleaned.removeprefix("```").strip()

		if cleaned.endswith("```"):
			cleaned = cleaned.removesuffix("```").strip()

		json_start = cleaned.find("[")
		if json_start == -1:
			json_start = cleaned.find("{")

		json_end = cleaned.rfind("]")
		if json_end == -1:
			json_end = cleaned.rfind("}")

		if json_start != -1 and json_end != -1:
			return cleaned[json_start : json_end + 1]

		return cleaned

	@staticmethod
	def _preserve_whitespace(original: str, translated: str) -> str:
		if not original:
			return translated
		leading_spaces = len(original) - len(original.lstrip(" "))
		trailing_spaces = len(original) - len(original.rstrip(" "))
		return (" " * leading_spaces) + translated.strip() + (" " * trailing_spaces)


class GroqService(TranslationService):
	"""
	A concrete implementation of TranslationService that uses the Groq API.
	Groq provides fast inference using OpenAI-compatible endpoints.
	"""

	def __init__(
		self, config: TranslationConfig, app_name: str | None = None, logger: logging.Logger | None = None
	):
		self.config = config
		self.app_name = app_name
		self.logger = logger or logging.getLogger(__name__)
		self.client = self._configure_client()
		self.context = self._fetch_context()

	def _configure_client(self):
		"""
		Configures and returns an OpenAI client pointing to Groq's API.
		"""
		try:
			from openai import OpenAI
		except ImportError:
			raise ImportError(
				"The 'openai' package is required for Groq support. Install it with: pip install openai"
			)

		if not self.config.api_key:
			raise ValueError("Groq API key not found in settings.")

		return OpenAI(api_key=self.config.api_key, base_url="https://api.groq.com/openai/v1")

	def _fetch_context(self) -> dict[str, Any]:
		"""
		Fetches translation context for the app.
		Priority:
		1. App DocType configuration (UI)
		2. 'translation_context' hook (Code)
		3. Default/Empty
		"""
		if not self.app_name:
			return {}

		import frappe

		context = {}

		# 1. Try App DocType
		try:
			if frappe.db.exists("App", self.app_name):
				app_doc = frappe.get_doc("App", self.app_name)

				if app_doc.domain:
					context["domain"] = app_doc.domain
				if app_doc.tone:
					context["tone"] = app_doc.tone
				if app_doc.description:
					context["description"] = app_doc.description

				if app_doc.do_not_translate:
					context["do_not_translate"] = [item.term for item in app_doc.do_not_translate]
		except Exception as e:
			self.logger.warning(f"Failed to fetch context from App DocType: {e}")

		# 2. Try Hook if UI context is empty
		try:
			hooks = frappe.get_hooks("translation_context", app_name=self.app_name)
			if hooks:
				for hook in hooks:
					hook_context = frappe.call(hook)
					if isinstance(hook_context, dict):
						hook_context.update(context)
						context = hook_context
		except Exception as e:
			self.logger.warning(f"Failed to fetch context from hook: {e}")

		# 3. Localization Profile (Takes precedence over App Context for glossary)
		if getattr(self.config, "localization_profile", None):
			try:
				profile = frappe.get_doc("Localization Profile", self.config.localization_profile)

				# Regional Glossary
				if profile.regional_glossary:
					if "glossary" not in context:
						context["glossary"] = {}

					for item in profile.regional_glossary:
						# Format: "Term": "Translation" (Context)
						term_key = item.english_term
						translation = item.localized_term
						if item.context:
							translation += f" ({item.context})"
						context["glossary"][term_key] = translation

				# Context Rules
				if profile.context_rules:
					if "context_rules" not in context:
						context["context_rules"] = []

					for rule in profile.context_rules:
						context["context_rules"].append(
							{
								"pattern": rule.source_pattern,
								"translation": rule.target_translation,
								"priority": rule.priority,
								"examples": rule.examples,
							}
						)

			except Exception as e:
				self.logger.warning(f"Failed to fetch Localization Profile: {e}")

		return context

	def translate(self, entries: list[dict[str, Any]]) -> list[dict[str, str]]:
		"""
		Translates a batch of entries using the Groq API.
		Includes retry logic and fallback to single-entry translation.
		"""
		# --- BATCH TRANSLATION ATTEMPT ---
		for attempt in range(self.config.max_batch_retries):
			try:
				prompt = self._build_batch_prompt(entries)
				self.logger.debug(f"Batch prompt:\n{prompt}")
				self.logger.info(
					f"  [API Call] Translating batch of {len(entries)} entries via Groq (Attempt {attempt + 1}/{self.config.max_batch_retries})"
				)

				response = self.client.chat.completions.create(
					model=self.config.model_name,
					messages=[
						{
							"role": "system",
							"content": "You are a professional translator. Always respond with valid JSON only.",
						},
						{"role": "user", "content": prompt},
					],
					temperature=0.3,
				)

				response_text = response.choices[0].message.content
				json_str = self._clean_json_response(response_text)
				translated_items = json.loads(json_str)

				if isinstance(translated_items, list) and len(translated_items) == len(entries):
					processed_translations = []
					for i, item in enumerate(translated_items):
						original_msgid = entries[i]["msgid"]
						translated_text = item.get("translated", "")
						preserved_text = self._preserve_whitespace(original_msgid, translated_text)
						processed_translations.append({"msgid": original_msgid, "msgstr": preserved_text})
					return processed_translations

			except (json.JSONDecodeError, Exception) as e:
				self.logger.warning(
					f"  [Warning] Batch translation attempt {attempt + 1}/{self.config.max_batch_retries} failed: {e}"
				)
				if attempt < self.config.max_batch_retries - 1:
					time.sleep(self.config.retry_wait_seconds)

		# --- FALLBACK TO SINGLE-ENTRY TRANSLATION ---
		self.logger.info(
			f"  [Info] Batch failed after {self.config.max_batch_retries} attempts. Switching to single-entry mode for this batch."
		)
		return [self._translate_single(entry) for entry in entries]

	def _translate_single(self, entry: dict[str, Any]) -> dict[str, str]:
		"""
		Translates a single entry, with retries.
		"""
		msgid = entry["msgid"]
		for attempt in range(self.config.max_single_retries):
			try:
				prompt = self._build_single_prompt(entry)
				self.logger.debug(f"Single entry prompt:\n{prompt}")
				self.logger.info(
					f"    [API Call] Translating single entry via Groq: '{msgid}' (Attempt {attempt + 1}/{self.config.max_single_retries})"
				)

				response = self.client.chat.completions.create(
					model=self.config.model_name,
					messages=[
						{
							"role": "system",
							"content": "You are a professional translator. Always respond with valid JSON only.",
						},
						{"role": "user", "content": prompt},
					],
					temperature=0.3,
				)

				response_text = response.choices[0].message.content
				json_str = self._clean_json_response(response_text)
				translated_item = json.loads(json_str)
				if isinstance(translated_item, dict) and "translated" in translated_item:
					translated_text = self._preserve_whitespace(msgid, translated_item["translated"])
					return {"msgid": msgid, "msgstr": translated_text}
			except (json.JSONDecodeError, Exception) as e:
				self.logger.warning(
					f"    [Warning] Single-entry attempt {attempt + 1}/{self.config.max_single_retries} failed for '{msgid}': {e}"
				)
				if attempt < self.config.max_single_retries - 1:
					time.sleep(self.config.retry_wait_seconds)

		self.logger.error(
			f"    [Error] Failed to translate '{msgid}' after {self.config.max_single_retries} attempts."
		)
		# Return None to skip this entry (don't write failed translations)
		return None

	def _build_batch_prompt(self, entries: list[dict[str, Any]]) -> str:
		base_prompt = (
			f"You are a translator specialized in ERP systems, translating to the language '{self.config.language_code}'.\n"
			"Translate the following texts, considering the context where they appear in the code (occurrences), "
			"developer comments (comment), and other flags (flags).\n"
		)

		if self.context:
			base_prompt += "\n**Application Context:**\n"
			if self.context.get("domain"):
				base_prompt += f"- Domain: {self.context['domain']}\n"
			if self.context.get("tone"):
				base_prompt += f"- Tone of Voice: {self.context['tone']}\n"
			if self.context.get("description"):
				base_prompt += f"- Description: {self.context['description']}\n"

			if self.context.get("glossary"):
				base_prompt += "\n**Glossary (Term -> Translation):**\n"
				for term, trans in self.context["glossary"].items():
					base_prompt += f"- {term}: {trans}\n"

			if self.context.get("do_not_translate"):
				base_prompt += "\n**DO NOT TRANSLATE these terms:**\n"
				base_prompt += ", ".join(self.context["do_not_translate"]) + "\n"

		# Inject Learning Examples
		base_prompt += self._fetch_learning_examples()

		base_prompt += (
			"\nReturn YOUR RESPONSE AS A SINGLE JSON ARRAY of objects, each with the key 'translated'.\n"
			"The output array must have exactly the same number of items as the input.\n"
			"Keep placeholders like `{0}` and HTML tags like `<strong>` intact."
		)
		if self.config.standardization_guide:
			base_prompt += f"\n\n**Standardization Guide:**\n{self.config.standardization_guide}\nFollow this guide strictly."

		items_to_translate = json.dumps(entries, indent=2, ensure_ascii=False)

		return (
			f"{base_prompt}\n\n"
			"Items to translate:\n"
			f"{items_to_translate}\n\n"
			"Output JSON Array (only the array of 'translated' objects):\n"
		)

	def _build_single_prompt(self, entry: dict[str, Any]) -> str:
		base_prompt = (
			f"You are a translator specialized in ERP systems, translating to the language '{self.config.language_code}'.\n"
			"Translate the text below, considering the context where it appears in the code (occurrences), "
			"developer comments (comment), and other flags (flags).\n"
		)

		if self.context:
			base_prompt += "\n**Application Context:**\n"
			if self.context.get("domain"):
				base_prompt += f"- Domain: {self.context['domain']}\n"
			if self.context.get("tone"):
				base_prompt += f"- Tone of Voice: {self.context['tone']}\n"
			if self.context.get("description"):
				base_prompt += f"- Description: {self.context['description']}\n"

			if self.context.get("glossary"):
				base_prompt += "\n**Glossary (Term -> Translation):**\n"
				for term, trans in self.context["glossary"].items():
					base_prompt += f"- {term}: {trans}\n"

			if self.context.get("do_not_translate"):
				base_prompt += "\n**DO NOT TRANSLATE these terms:**\n"
				base_prompt += ", ".join(self.context["do_not_translate"]) + "\n"

		base_prompt += (
			"\nReturn YOUR RESPONSE AS A SINGLE JSON OBJECT with the key 'translated'.\n"
			"Keep placeholders like `{0}` and HTML tags like `<strong>` intact."
		)
		if self.config.standardization_guide:
			base_prompt += f"\n\n**Standardization Guide:**\n{self.config.standardization_guide}\nFollow this guide strictly."

		item_to_translate = json.dumps(entry, indent=2, ensure_ascii=False)

		return (
			f"{base_prompt}\n\n"
			"Item to translate:\n"
			f"{item_to_translate}\n\n"
			"Output JSON Object (only the 'translated' object):\n"
		)

	@staticmethod
	def _clean_json_response(text: str) -> str:
		cleaned = text.strip()
		if cleaned.startswith("```json"):
			cleaned = cleaned.removeprefix("```json").strip()
		elif cleaned.startswith("```"):
			cleaned = cleaned.removeprefix("```").strip()

		if cleaned.endswith("```"):
			cleaned = cleaned.removesuffix("```").strip()

		json_start = cleaned.find("[")
		if json_start == -1:
			json_start = cleaned.find("{")

		json_end = cleaned.rfind("]")
		if json_end == -1:
			json_end = cleaned.rfind("}")

		if json_start != -1 and json_end != -1:
			return cleaned[json_start : json_end + 1]

		return cleaned

	@staticmethod
	def _preserve_whitespace(original: str, translated: str) -> str:
		if not original:
			return translated
		leading_spaces = len(original) - len(original.lstrip(" "))
		trailing_spaces = len(original) - len(original.rstrip(" "))
		return (" " * leading_spaces) + translated.strip() + (" " * trailing_spaces)


class OpenRouterService(TranslationService):
	"""
	A concrete implementation of TranslationService that uses the OpenRouter API.
	OpenRouter provides access to 500+ models via OpenAI-compatible endpoints.
	"""

	def __init__(
		self, config: TranslationConfig, app_name: str | None = None, logger: logging.Logger | None = None
	):
		self.config = config
		self.app_name = app_name
		self.logger = logger or logging.getLogger(__name__)
		self.client = self._configure_client()
		self.context = self._fetch_context()

	def _configure_client(self):
		"""
		Configures and returns an OpenAI client pointing to OpenRouter's API.
		"""
		try:
			from openai import OpenAI
		except ImportError:
			raise ImportError(
				"The 'openai' package is required for OpenRouter support. Install it with: pip install openai"
			)

		if not self.config.api_key:
			raise ValueError("OpenRouter API key not found in settings.")

		return OpenAI(api_key=self.config.api_key, base_url="https://openrouter.ai/api/v1")

	def _fetch_context(self) -> dict:
		"""
		Fetches context for the app being translated.
		"""
		context = {}
		if not self.app_name:
			return context
		try:
			import frappe

			hooks = frappe.get_hooks("translation_context", app_name=self.app_name)
			if hooks:
				for hook in hooks:
					context.update(frappe.get_attr(hook)())
		except Exception as e:
			self.logger.warning(f"Failed to fetch context from hook: {e}")
		return context

	def translate(self, entries: list[dict[str, Any]]) -> list[dict[str, str]]:
		"""
		Translates a list of entries using the OpenRouter API.
		"""
		if not entries:
			return []

		# Try batch translation first
		for attempt in range(1, self.config.max_batch_retries + 1):
			try:
				self.logger.info(
					f"[API Call] Translating batch of {len(entries)} entries via OpenRouter (Attempt {attempt}/{self.config.max_batch_retries})"
				)
				prompt = self._build_batch_prompt(entries)

				response = self.client.chat.completions.create(
					model=self.config.model_name,
					messages=[
						{
							"role": "system",
							"content": "You are a professional translator. Always respond with valid JSON only.",
						},
						{"role": "user", "content": prompt},
					],
					temperature=0.3,
				)

				raw_content = response.choices[0].message.content
				cleaned_content = self._clean_json_response(raw_content)
				translations_list = json.loads(cleaned_content)

				if len(translations_list) != len(entries):
					raise ValueError(f"Expected {len(entries)} translations, got {len(translations_list)}")

				results = []
				for entry, translation in zip(entries, translations_list, strict=False):
					original_msgid = entry["msgid"]
					translated_text = translation.get("translated", "")
					final_text = self._preserve_whitespace(original_msgid, translated_text)
					results.append({"msgid": original_msgid, "msgstr": final_text})

				return results

			except Exception as e:
				self.logger.warning(
					f"[Warning] Batch attempt {attempt}/{self.config.max_batch_retries} failed: {e}"
				)
				if attempt < self.config.max_batch_retries:
					time.sleep(self.config.retry_wait_seconds)

		# Fallback to single-entry translation
		self.logger.warning("[Warning] Batch translation failed. Falling back to single-entry mode.")
		return [self._translate_single(entry) for entry in entries]

	def _translate_single(self, entry: dict) -> dict[str, str]:
		"""
		Translates a single entry, with retries.
		"""
		original_msgid = entry["msgid"]

		for attempt in range(1, self.config.max_single_retries + 1):
			try:
				self.logger.info(
					f"[API Call] Translating single entry via OpenRouter: '{original_msgid[:50]}...' (Attempt {attempt}/{self.config.max_single_retries})"
				)
				prompt = self._build_single_prompt(entry)

				response = self.client.chat.completions.create(
					model=self.config.model_name,
					messages=[
						{
							"role": "system",
							"content": "You are a professional translator. Always respond with valid JSON only.",
						},
						{"role": "user", "content": prompt},
					],
					temperature=0.3,
				)

				raw_content = response.choices[0].message.content
				cleaned_content = self._clean_json_response(raw_content)
				translation_obj = json.loads(cleaned_content)
				translated_text = translation_obj.get("translated", "")
				final_text = self._preserve_whitespace(original_msgid, translated_text)
				return {"msgid": original_msgid, "msgstr": final_text}

			except Exception as e:
				self.logger.warning(
					f"[Warning] Single-entry attempt {attempt}/{self.config.max_single_retries} failed for '{original_msgid[:50]}...': {e}"
				)
				if attempt < self.config.max_single_retries:
					time.sleep(self.config.retry_wait_seconds)

		self.logger.error(
			f"[Error] Failed to translate '{original_msgid[:50]}...' after {self.config.max_single_retries} attempts."
		)
		# Return None to skip this entry (don't write failed translations)
		return None

	def _build_batch_prompt(self, entries: list[dict]) -> str:
		"""Builds a prompt for batch translation."""
		guide = self.config.standardization_guide or ""
		lang = self.config.language_code or "the target language"

		items = [{"msgid": e["msgid"], "context": e.get("context", {})} for e in entries]

		prompt = f"""You are a translator specialized in ERP systems, translating to the language '{lang}'.
Translate the following texts, considering the context where they appear in the code (occurrences), developer comments (comment), and other flags (flags).

{guide}

{self._fetch_learning_examples()}

Return YOUR RESPONSE AS A SINGLE JSON ARRAY of objects, each with the key 'translated'.
The output array must have exactly the same number of items as the input.
Keep placeholders like `{{0}}` and HTML tags like `<strong>` intact.

Items to translate:
{json.dumps(items, indent=2, ensure_ascii=False)}

Output JSON Array (only the array of 'translated' objects):
"""
		return prompt

	def _build_single_prompt(self, entry: dict) -> str:
		"""Builds a prompt for single-entry translation."""
		guide = self.config.standardization_guide or ""
		lang = self.config.language_code or "the target language"
		msgid = entry["msgid"]
		context = entry.get("context", {})

		prompt = f"""You are a translator specialized in ERP systems, translating to the language '{lang}'.
Translate the following text, considering its context.

{guide}

Text to translate: "{msgid}"
Context: {json.dumps(context, ensure_ascii=False)}

Return ONLY a JSON object with the key 'translated':
{{"translated": "your translation here"}}
"""
		return prompt

	@staticmethod
	def _clean_json_response(response_text: str) -> str:
		"""Cleans markdown or extra text from the LLM response."""
		cleaned = response_text.strip()

		if cleaned.startswith("```json"):
			cleaned = cleaned[7:]
		if cleaned.startswith("```"):
			cleaned = cleaned[3:]
		if cleaned.endswith("```"):
			cleaned = cleaned[:-3]

		cleaned = cleaned.strip()

		json_start = cleaned.find("[")
		if json_start == -1:
			json_start = cleaned.find("{")

		json_end = cleaned.rfind("]")
		if json_end == -1:
			json_end = cleaned.rfind("}")

		if json_start != -1 and json_end != -1:
			return cleaned[json_start : json_end + 1]

		return cleaned

	@staticmethod
	def _preserve_whitespace(original: str, translated: str) -> str:
		if not original:
			return translated
		leading_spaces = len(original) - len(original.lstrip(" "))
		trailing_spaces = len(original) - len(original.rstrip(" "))
		return (" " * leading_spaces) + translated.strip() + (" " * trailing_spaces)
