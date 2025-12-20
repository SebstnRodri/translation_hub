# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

"""
Base classes and data structures for the agent pipeline.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TranslationEntry:
	"""Represents a single translation entry flowing through the pipeline."""

	msgid: str
	msgstr: str = ""
	context: str = ""
	occurrences: list[tuple[str, str]] = field(default_factory=list)
	flags: list[str] = field(default_factory=list)
	comment: str = ""

	# Pipeline metadata
	raw_translation: str = ""  # Initial translation from TranslatorAgent
	reviewed_translation: str = ""  # After RegionalReviewerAgent

	def to_dict(self) -> dict[str, Any]:
		"""Convert to dictionary for LLM prompt."""
		return {
			"msgid": self.msgid,
			"context": self.context,
			"occurrences": self.occurrences,
			"flags": self.flags,
			"comment": self.comment,
		}


@dataclass
class TranslationResult:
	"""Result of the complete agent pipeline for a single entry."""

	msgid: str
	msgstr: str
	quality_score: float = 0.0
	needs_human_review: bool = False
	review_reasons: list[str] = field(default_factory=list)
	agent_notes: dict[str, str] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		"""Convert to dictionary for saving."""
		return {
			"msgid": self.msgid,
			"msgstr": self.msgstr,
			"quality_score": self.quality_score,
			"needs_human_review": self.needs_human_review,
			"review_reasons": self.review_reasons,
		}


class BaseAgent:
	"""Base class for all translation agents."""

	def __init__(self, config, logger=None):
		self.config = config
		self.logger = logger
		self._log_prefix = "[BaseAgent]"

	def log_info(self, message: str):
		if self.logger:
			self.logger.info(f"{self._log_prefix} {message}")

	def log_warning(self, message: str):
		if self.logger:
			self.logger.warning(f"{self._log_prefix} {message}")

	def log_error(self, message: str):
		if self.logger:
			self.logger.error(f"{self._log_prefix} {message}")

	def log_debug(self, message: str):
		if self.logger:
			self.logger.debug(f"{self._log_prefix} {message}")
