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
				translations.append({"msgid": msgid, "msgstr": f"[TRANSLATION_FAILED] {msgid}"})
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

		return context

	def _configure_model(self) -> genai.GenerativeModel:
		"""
		Configures and returns a Google Gemini model instance.
		"""
		if not self.config.api_key:
			raise ValueError("API key not found in settings.")

		genai.configure(api_key=self.config.api_key)
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
					f"  [API Call] Translating batch of {len(entries)} entries (Attempt {attempt + 1}/{self.config.max_batch_retries})"
				)
				response = self.model.generate_content(prompt)
				json_str = self._clean_json_response(response.text)
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
					f"    [API Call] Translating single entry: '{msgid}' (Attempt {attempt + 1}/{self.config.max_single_retries})"
				)
				response = self.model.generate_content(prompt)
				json_str = self._clean_json_response(response.text)
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
		return {"msgid": msgid, "msgstr": f"[TRANSLATION_FAILED] {msgid}"}

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
				"The 'openai' package is required for Groq support. " "Install it with: pip install openai"
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
		return {"msgid": msgid, "msgstr": f"[TRANSLATION_FAILED] {msgid}"}

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
