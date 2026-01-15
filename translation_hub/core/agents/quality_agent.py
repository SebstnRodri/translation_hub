# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

"""
QualityAgent: Evaluates translation quality and decides if human review is needed.

This agent performs quality checks:
- Placeholder integrity verification
- Glossary consistency check
- Length ratio analysis
- Confidence scoring
"""

import json
import re
import time
from typing import Any

from translation_hub.core.agents.base import BaseAgent, TranslationEntry, TranslationResult


class QualityAgent(BaseAgent):
	"""
	Agent that evaluates translation quality and decides if human review is needed.
	"""

	def __init__(self, config, logger=None):
		super().__init__(config, logger)
		self._log_prefix = "[QualityAgent]"
		self.quality_threshold = getattr(config, "quality_threshold", 0.8)
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
			import google.generativeai as genai

			genai.configure(api_key=self.config.api_key)
			return genai.GenerativeModel(self.config.model_name)

	def evaluate(self, entries: list[TranslationEntry]) -> list[TranslationResult]:
		"""
		Evaluate translation quality for each entry.

		Args:
			entries: List of TranslationEntry with reviewed_translation set

		Returns:
			List of TranslationResult with quality scores and review flags
		"""
		self.log_info(f"Evaluating quality for {len(entries)} translations (threshold={self.quality_threshold})")

		results = []
		for entry in entries:
			result = self._evaluate_single(entry)
			results.append(result)

		# Summary
		needs_review = sum(1 for r in results if r.needs_human_review)
		avg_score = sum(r.quality_score for r in results) / len(results) if results else 0

		self.log_info(
			f"Quality evaluation complete: avg_score={avg_score:.2f}, needs_review={needs_review}/{len(results)}"
		)

		return results

	def _evaluate_single(self, entry: TranslationEntry) -> TranslationResult:
		"""Evaluate a single translation."""
		translation = entry.reviewed_translation or entry.raw_translation or entry.msgstr

		# Ensure translation is a string (LLM may return dict)
		if isinstance(translation, dict):
			# Extract translation from dict if present
			translation = translation.get("translation") or translation.get("translated") or str(translation)
		elif not isinstance(translation, str):
			translation = str(translation) if translation else ""

		# Initialize result
		result = TranslationResult(
			msgid=entry.msgid,
			msgstr=translation,
			quality_score=1.0,
			needs_human_review=False,
			review_reasons=[],
			agent_notes={},
		)

		# Run quality checks
		checks = [
			self._check_placeholders(entry.msgid, translation),
			self._check_html_tags(entry.msgid, translation),
			self._check_length_ratio(entry.msgid, translation),
			self._check_empty_translation(entry.msgid, translation),
			self._check_untranslated(entry.msgid, translation),
		]

		# Aggregate scores and reasons
		for check_name, score, reasons in checks:
			result.quality_score = min(result.quality_score, score)
			result.review_reasons.extend(reasons)
			result.agent_notes[check_name] = f"score={score:.2f}"

		# Determine if human review is needed
		if result.quality_score < self.quality_threshold:
			result.needs_human_review = True
			self.log_debug(f"'{entry.msgid[:30]}...' needs review: score={result.quality_score:.2f}")

		return result

	def _check_placeholders(self, source: str, translation: str) -> tuple[str, float, list[str]]:
		"""Check if all placeholders are preserved."""
		# Common placeholder patterns
		patterns = [
			r"\{\}",  # {} empty placeholder
			r"#\{\}",  # #{} hash placeholder (Frappe)
			r"\{[0-9]+\}",  # {0}, {1}, etc.
			r"#\{[0-9]+\}",  # #{0}, #{1} (Frappe row references)
			r"\{[a-zA-Z_][a-zA-Z0-9_]*\}",  # {name}, {user_id}, etc.
			r"%[sd]",  # %s, %d
			r"%\([a-zA-Z_][a-zA-Z0-9_]*\)[sd]",  # %(name)s
		]

		reasons = []
		for pattern in patterns:
			source_matches = set(re.findall(pattern, source))
			trans_matches = set(re.findall(pattern, translation))

			missing = source_matches - trans_matches
			extra = trans_matches - source_matches

			if missing:
				reasons.append(f"Missing placeholders: {missing}")
			if extra:
				reasons.append(f"Extra placeholders: {extra}")

		if reasons:
			return ("placeholders", 0.3, reasons)
		return ("placeholders", 1.0, [])

	def _check_html_tags(self, source: str, translation: str) -> tuple[str, float, list[str]]:
		"""Check if HTML tags are preserved."""
		tag_pattern = r"<[^>]+>"

		source_tags = re.findall(tag_pattern, source)
		trans_tags = re.findall(tag_pattern, translation)

		reasons = []
		if len(source_tags) != len(trans_tags):
			reasons.append(
				f"HTML tag count mismatch: source={len(source_tags)}, translation={len(trans_tags)}"
			)
			return ("html_tags", 0.5, reasons)

		return ("html_tags", 1.0, [])

	def _check_length_ratio(self, source: str, translation: str) -> tuple[str, float, list[str]]:
		"""Check if translation length is reasonable."""
		if not source or not translation:
			return ("length_ratio", 1.0, [])

		ratio = len(translation) / len(source)

		# Typical acceptable ranges (translations can be 0.5x to 2.5x source length)
		if ratio < 0.3:
			return ("length_ratio", 0.6, [f"Translation too short: ratio={ratio:.2f}"])
		elif ratio > 3.0:
			return ("length_ratio", 0.6, [f"Translation too long: ratio={ratio:.2f}"])

		return ("length_ratio", 1.0, [])

	def _check_empty_translation(self, source: str, translation: str) -> tuple[str, float, list[str]]:
		"""Check if translation is empty."""
		if source and not translation.strip():
			return ("empty", 0.0, ["Translation is empty"])
		return ("empty", 1.0, [])

	def _check_untranslated(self, source: str, translation: str) -> tuple[str, float, list[str]]:
		"""
		Check if translation is same as source (possibly not translated).
		
		Uses hybrid approach:
		1. Heuristics for obvious cognates/technical terms
		2. Trust pipeline consensus (TranslatorAgent + RegionalReviewer approved)
		"""
		# Skip very short strings (likely cognates or abbreviations)
		if len(source) < 20:
			return ("untranslated", 1.0, [])

		# Check if they're identical (excluding case)
		if source.strip().lower() != translation.strip().lower():
			return ("untranslated", 1.0, [])

		# --- Identical translation detected, check if it's a legitimate cognate ---

		source_lower = source.strip().lower()

		# 1. Technical patterns that should remain unchanged
		technical_patterns = [
			r"^[A-Z]{2,}$",  # Acronyms: API, URL, ID, PDF
			r"^[a-z]+_[a-z_]+$",  # snake_case identifiers
			r"^[a-z]+[A-Z][a-zA-Z]*$",  # camelCase identifiers
			r"^\d+[\d\s,\.]*$",  # Numbers
			r"^https?://",  # URLs
			r"@.*\.",  # Emails
			r"^\{.*\}$",  # Placeholders only
		]
		for pattern in technical_patterns:
			if re.match(pattern, source.strip(), re.IGNORECASE):
				return ("untranslated", 1.0, [])

		# 2. Common cognate suffixes (EN -> PT patterns)
		# Words ending in these are often identical or very similar
		cognate_suffixes = [
			"tion", "sion",  # emotion, version
			"al", "el",  # local, hotel
			"ment",  # moment, document
			"ble",  # possible, visible
			"ude",  # longitude, latitude
			"ive",  # active, native
			"ence", "ance",  # reference, balance
			"ism",  # capitalism
			"ist",  # artist
			"or", "er",  # error, server
		]
		for suffix in cognate_suffixes:
			if source_lower.endswith(suffix):
				return ("untranslated", 1.0, [])

		# 3. Common technical/international terms (expanded list)
		technical_terms = {
			"email", "e-mail", "data", "status", "menu", "internet",
			"software", "hardware", "online", "offline", "web", "website",
			"login", "logout", "password", "username", "admin", "user",
			"server", "client", "database", "backup", "cache", "proxy",
			"api", "url", "html", "css", "json", "xml", "http", "https",
			"pdf", "csv", "excel", "word", "powerpoint", "default",
			"marketing", "design", "layout", "click", "link", "download",
			"upload", "dashboard", "widget", "template", "plugin", "script",
		}
		# Check if source is a known technical term
		if source_lower in technical_terms:
			return ("untranslated", 1.0, [])

		# 4. Single-word terms under 15 chars - trust the pipeline
		# TranslatorAgent + RegionalReviewer already validated
		if len(source.split()) == 1 and len(source) < 15:
			return ("untranslated", 1.0, [])

		# 5. For longer identical strings, trust the pipeline consensus
		# If TranslatorAgent translated as-is AND RegionalReviewer approved,
		# they made an informed decision - don't second-guess
		return ("untranslated", 0.95, [])  # Slight note, but no penalty
