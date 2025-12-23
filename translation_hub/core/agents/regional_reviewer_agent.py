# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

"""
RegionalReviewerAgent: Applies regional and cultural adjustments.

This agent reviews translations and adjusts them based on:
- Regional Expert Profile (cultural context, formality, etc.)
- Forbidden terms detection and replacement
- Preferred synonyms application
"""

import json
import time
from typing import Any

from translation_hub.core.agents.base import BaseAgent, TranslationEntry


class RegionalReviewerAgent(BaseAgent):
	"""
	Agent specialized in regional/cultural review of translations.
	Applies adjustments based on Regional Expert Profile.
	"""

	def __init__(self, config, regional_profile=None, logger=None):
		super().__init__(config, logger)
		self._log_prefix = "[RegionalReviewerAgent]"
		self.regional_profile = regional_profile
		self.profile_context = self._load_profile_context()
		self.client = self._configure_client()

	def _load_profile_context(self) -> dict[str, Any]:
		"""Load context from Regional Expert Profile."""
		self.log_info(f"Loading profile context for: '{self.regional_profile}'")
		
		if not self.regional_profile:
			self.log_info("No regional profile configured, skipping")
			return {}

		try:
			import frappe

			if frappe.db.exists("Regional Expert Profile", self.regional_profile):
				profile = frappe.get_doc("Regional Expert Profile", self.regional_profile)
				context = profile.get_context_for_prompt()
				self.log_info(f"Loaded profile '{self.regional_profile}' with {len(context)} context keys")
				return context
			else:
				self.log_warning(f"Profile '{self.regional_profile}' not found in database")
		except Exception as e:
			self.log_warning(f"Failed to load Regional Expert Profile: {e}")

		return {}

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
			import google.generativeai as genai

			genai.configure(api_key=self.config.api_key)
			return genai.GenerativeModel(self.config.model_name)

	def review(self, entries: list[TranslationEntry]) -> list[TranslationEntry]:
		"""
		Review and adjust translations for regional appropriateness.

		Args:
			entries: List of TranslationEntry objects with raw_translation set

		Returns:
			Same entries with reviewed_translation populated
		"""
		if not self.profile_context:
			self.log_info("No regional profile configured, skipping review")
			for entry in entries:
				entry.reviewed_translation = entry.raw_translation
			return entries

		self.log_info(
			f"Reviewing {len(entries)} translations for region: {self.profile_context.get('region', 'unknown')}"
		)

		# First pass: Check for forbidden terms (fast, no LLM needed)
		for entry in entries:
			entry.reviewed_translation = self._apply_local_rules(entry.raw_translation)

		# Second pass: LLM review for cultural nuances
		prompt = self._build_review_prompt(entries)

		for attempt in range(self.config.max_batch_retries):
			try:
				response = self._call_llm(prompt)
				reviewed = self._parse_response(response, len(entries))

				if len(reviewed) == len(entries):
					for i, entry in enumerate(entries):
						if reviewed[i]:  # Only update if LLM provided a review
							entry.reviewed_translation = reviewed[i]
						entry.msgstr = entry.reviewed_translation
					self.log_info(f"Successfully reviewed {len(entries)} entries")
					return entries

			except Exception as e:
				self.log_warning(f"Review attempt {attempt + 1} failed: {e}")
				if attempt < self.config.max_batch_retries - 1:
					time.sleep(self.config.retry_wait_seconds)

		# If LLM review fails, use local rules only
		self.log_warning("LLM review failed, using local rules only")
		for entry in entries:
			entry.msgstr = entry.reviewed_translation
		return entries

	def _apply_local_rules(self, text: str) -> str:
		"""Apply local rules without LLM (forbidden terms, synonyms)."""
		result = text

		# Apply preferred synonyms
		synonyms = self.profile_context.get("preferred_synonyms", {})
		for original, info in synonyms.items():
			if original.lower() in result.lower():
				# Simple case-preserving replacement
				import re

				pattern = re.compile(re.escape(original), re.IGNORECASE)
				result = pattern.sub(info["preferred"], result)

		return result

	def _build_review_prompt(self, entries: list[TranslationEntry]) -> str:
		"""Build the review prompt with regional context."""
		region = self.profile_context.get("region", "unknown")
		formality = self.profile_context.get("formality_level", "Neutral")
		cultural = self.profile_context.get("cultural_context", "")
		forbidden = self.profile_context.get("forbidden_terms", [])
		jargon = self.profile_context.get("industry_jargon", {})

		prompt = f"""You are a regional language expert for {region}.
Your task is to review translations and adjust them for regional appropriateness.

**Formality Level:** {formality}
**Cultural Context:** {cultural}

"""
		if forbidden:
			prompt += "**FORBIDDEN TERMS (must replace):**\n"
			for term in forbidden:
				prompt += (
					f"- '{term['term']}' - Reason: {term.get('reason', 'Not appropriate for this region')}\n"
				)
			prompt += "\n"

		if jargon:
			prompt += "**Industry-Specific Terms:**\n"
			for eng, local in jargon.items():
				prompt += f"- {eng} → {local}\n"
			prompt += "\n"

		# Build items list
		items = []
		for entry in entries:
			items.append({"source": entry.msgid, "translation": entry.raw_translation})

		prompt += f"""
Review these translations and adjust for regional/cultural appropriateness:
{json.dumps(items, indent=2, ensure_ascii=False)}

Return ONLY a JSON array with the reviewed translations (same order).
If no changes needed, return the original translation.
["reviewed text 1", "reviewed text 2", ...]
"""
		return prompt

	def _call_llm(self, prompt: str) -> str:
		"""Call the LLM and return the response text."""
		provider = getattr(self.config, "llm_provider", "Gemini")

		if provider in ("Groq", "OpenRouter"):
			response = self.client.chat.completions.create(
				model=self.config.model_name,
				messages=[
					{
						"role": "system",
						"content": "You are a regional language expert. Focus on cultural and regional appropriateness. Always respond with valid JSON.",
					},
					{"role": "user", "content": prompt},
				],
				temperature=0.2,
			)
			return response.choices[0].message.content
		else:
			response = self.client.generate_content(prompt)
			return response.text

	def _parse_response(self, response: str, expected_count: int) -> list[str]:
		"""Parse the LLM response into a list of reviewed translations."""
		cleaned = response.strip()
		if cleaned.startswith("```json"):
			cleaned = cleaned[7:]
		elif cleaned.startswith("```"):
			cleaned = cleaned[3:]
		if cleaned.endswith("```"):
			cleaned = cleaned[:-3]

		parsed = json.loads(cleaned.strip())

		if isinstance(parsed, list):
			# Normalize items: ensure each is a string
			normalized = []
			for item in parsed:
				if isinstance(item, str):
					normalized.append(item)
				elif isinstance(item, dict):
					# Extract translation from dict
					normalized.append(
						item.get("translation") or item.get("translated") or item.get("text") or str(item)
					)
				else:
					normalized.append(str(item) if item else "")
			return normalized
		else:
			raise ValueError(f"Expected list, got {type(parsed)}")
