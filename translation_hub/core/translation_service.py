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

			# Simple mock translation: add [ES] prefix
			# Preserve placeholders and HTML tags
			mock_translation = f"[ES] {msgid}"

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

	def __init__(self, config: TranslationConfig, logger: logging.Logger | None = None):
		self.config = config
		self.logger = logger or logging.getLogger(__name__)
		self.model = self._configure_model()

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
			"Você é um tradutor especializado em sistemas ERP, traduzindo para o português do Brasil.\n"
			"Traduza os textos a seguir, considerando o contexto de onde eles aparecem no código (occurrences), "
			"comentários de desenvolvedores (comment), e outras flags (flags).\n"
			"Retorne SUA RESPOSTA COMO UM ÚNICO ARRAY JSON de objetos, cada um com a chave 'translated'.\n"
			"O array de saída deve ter exatamente o mesmo número de itens da entrada.\n"
			"Mantenha placeholders como `{0}` e tags HTML como `<strong>` intactos."
		)
		if self.config.standardization_guide:
			base_prompt += f"\n\n**Guia de Padronização:**\n{self.config.standardization_guide}\nSiga este guia rigorosamente."

		items_to_translate = json.dumps(entries, indent=2, ensure_ascii=False)

		return (
			f"{base_prompt}\n\n"
			"Itens a traduzir:\n"
			f"{items_to_translate}\n\n"
			"Array JSON de saída (apenas o array de objetos 'translated'):\n"
		)

	def _build_single_prompt(self, entry: dict[str, Any]) -> str:
		base_prompt = (
			"Você é um tradutor especializado em sistemas ERP, traduzindo para o português do Brasil.\n"
			"Traduza o texto a seguir, considerando o contexto de onde ele aparece no código (occurrences), "
			"comentários de desenvolvedores (comment), e outras flags (flags).\n"
			"Retorne SUA RESPOSTA COMO UM ÚNICO OBJETO JSON com a chave 'translated'.\n"
			"Mantenha placeholders como `{0}` e tags HTML como `<strong>` intactos."
		)
		if self.config.standardization_guide:
			base_prompt += f"\n\n**Guia de Padronização:**\n{self.config.standardization_guide}\nSiga este guia rigorosamente."

		item_to_translate = json.dumps(entry, indent=2, ensure_ascii=False)

		return (
			f"{base_prompt}\n\n"
			"Item a traduzir:\n"
			f"{item_to_translate}\n\n"
			"Objeto JSON de saída (apenas o objeto 'translated'):\n"
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
