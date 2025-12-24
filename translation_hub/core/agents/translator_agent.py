# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

"""
TranslatorAgent: Specialized in domain-specific translation.

This agent performs the initial translation, focusing on:
- ERP/business domain terminology
- Technical accuracy
- Placeholder preservation
"""

import json
import time
from typing import Any

from translation_hub.core.agents.base import BaseAgent, TranslationEntry


class TranslatorAgent(BaseAgent):
	"""
	Agent specialized in domain-specific translation.
	Performs the initial translation with ERP context.
	"""

	def __init__(self, config, app_name: str | None = None, logger=None):
		super().__init__(config, logger)
		self._log_prefix = "[TranslatorAgent]"
		self.app_name = app_name
		self.client = self._configure_client()

	def _configure_client(self):
		"""Configure the LLM client based on settings."""
		provider = getattr(self.config, "llm_provider", "Gemini")

		if provider == "Groq":
			from openai import OpenAI

			return OpenAI(api_key=self.config.api_key, base_url="https://api.groq.com/openai/v1")
		elif provider == "OpenRouter":
			from openai import OpenAI

			return OpenAI(api_key=self.config.api_key, base_url="https://openrouter.ai/api/v1")
		else:
			# Gemini
			import google.generativeai as genai

			genai.configure(api_key=self.config.api_key)
			return genai.GenerativeModel(self.config.model_name)

	def translate(self, entries: list[TranslationEntry]) -> list[TranslationEntry]:
		"""
		Translate a batch of entries.

		Args:
			entries: List of TranslationEntry objects to translate

		Returns:
			Same entries with raw_translation populated
		"""
		self.log_info(f"Translating batch of {len(entries)} entries")

		prompt = self._build_prompt(entries)

		for attempt in range(self.config.max_batch_retries):
			try:
				response = self._call_llm(prompt)
				translations = self._parse_response(response, len(entries))

				if len(translations) == len(entries):
					for i, entry in enumerate(entries):
						entry.raw_translation = translations[i]
						entry.msgstr = translations[i]  # Initial value
					self.log_info(f"Successfully translated {len(entries)} entries")
					return entries

			except Exception as e:
				self.log_warning(f"Attempt {attempt + 1}/{self.config.max_batch_retries} failed: {e}")
				if attempt < self.config.max_batch_retries - 1:
					time.sleep(self.config.retry_wait_seconds)

		# Fallback to single-entry translation
		self.log_info("Falling back to single-entry translation")
		return self._translate_single(entries)

	def _translate_single(self, entries: list[TranslationEntry]) -> list[TranslationEntry]:
		"""Fallback: translate entries one by one."""
		for entry in entries:
			try:
				prompt = self._build_single_prompt(entry)
				response = self._call_llm(prompt)
				translation = self._parse_single_response(response)
				entry.raw_translation = translation
				entry.msgstr = translation
			except Exception as e:
				self.log_error(f"Failed to translate '{entry.msgid}': {e}")
				entry.raw_translation = ""
				entry.msgstr = ""
		return entries

	def _build_prompt(self, entries: list[TranslationEntry]) -> str:
		"""Build the batch translation prompt."""
		base_prompt = f"""You are a professional translator specialized in ERP/business software.
Translate the following texts to '{self.config.language_code}'.

CRITICAL RULES - MUST FOLLOW EXACTLY:
1. PLACEHOLDERS - Keep EXACTLY as they appear:
   - Empty: {{}} and #{{}} must remain as {{}} and #{{}}
   - Numbered: {{0}}, {{1}}, #{{0}} must NOT be changed
   - Named: {{name}}, %(user)s must remain identical
   - DO NOT add numbers to empty placeholders

2. HTML TAGS - PRESERVE EXACTLY AS-IS:
   - <b>text</b> must remain <b>texto</b> (NOT "texto" or **texto**)
   - <strong>, <em>, <br>, </a>, etc. must be kept unchanged
   - Same number of opening and closing tags as source
   - Do NOT replace HTML tags with quotes, asterisks or other formatting

3. Maintain formality level and use ERP/business terminology

"""
		if self.config.standardization_guide:
			base_prompt += f"\n**Standardization Guide:**\n{self.config.standardization_guide}\n\n"

		items = [entry.to_dict() for entry in entries]
		base_prompt += f"""
Items to translate:
{json.dumps(items, indent=2, ensure_ascii=False)}

Return ONLY a JSON array with the translations in the same order:
["translated text 1", "translated text 2", ...]
"""
		return base_prompt

	def _build_single_prompt(self, entry: TranslationEntry) -> str:
		"""Build prompt for a single entry."""
		return f"""You are a professional translator specialized in ERP/business software.
Translate to '{self.config.language_code}':

Source: {entry.msgid}
Context: {entry.context}
Occurrences: {entry.occurrences}

CRITICAL RULES:
- Keep placeholders {{0}}, %s, {{name}} etc. EXACTLY as-is
- Keep HTML tags <b>, <strong>, <br>, etc. EXACTLY as-is (do NOT replace with quotes)
- Use ERP/business terminology

Return ONLY a JSON object: {{"translated": "your translation"}}
"""

	def _call_llm(self, prompt: str) -> str:
		"""Call the LLM and return the response text."""
		provider = getattr(self.config, "llm_provider", "Gemini")

		if provider in ("Groq", "OpenRouter"):
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
			content = response.choices[0].message.content
			if not content or not content.strip():
				raise ValueError(f"Empty response from {provider} API")
			return content
		else:
			# Gemini
			response = self.client.generate_content(prompt)
			# Handle blocked or empty responses
			if not response.text:
				# Check if blocked by safety filters
				if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
					raise ValueError(f"Gemini blocked: {response.prompt_feedback}")
				raise ValueError("Empty response from Gemini API")
			return response.text

	def _parse_response(self, response: str, expected_count: int) -> list[str]:
		"""Parse the LLM response into a list of translations."""
		if not response or not response.strip():
			raise ValueError("Empty response received from LLM")
		
		cleaned = self._clean_json_response(response)
		if not cleaned:
			raise ValueError(f"Failed to extract JSON from response: {response[:100]}")
		
		parsed = json.loads(cleaned)

		if isinstance(parsed, list):
			return parsed
		elif isinstance(parsed, dict) and "translations" in parsed:
			return parsed["translations"]
		else:
			raise ValueError(f"Unexpected response format: {type(parsed)}")

	def _parse_single_response(self, response: str) -> str:
		"""Parse single entry response."""
		cleaned = self._clean_json_response(response)
		parsed = json.loads(cleaned)

		if isinstance(parsed, dict) and "translated" in parsed:
			return parsed["translated"]
		elif isinstance(parsed, str):
			return parsed
		else:
			raise ValueError(f"Unexpected response format: {type(parsed)}")

	@staticmethod
	def _clean_json_response(text: str) -> str:
		"""Clean markdown code blocks from JSON response."""
		cleaned = text.strip()
		if cleaned.startswith("```json"):
			cleaned = cleaned[7:]
		elif cleaned.startswith("```"):
			cleaned = cleaned[3:]
		if cleaned.endswith("```"):
			cleaned = cleaned[:-3]
		return cleaned.strip()
