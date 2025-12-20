# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

"""
Agent Module for Translation Hub.

This module contains specialized AI agents for the multi-agent translation pipeline:
- TranslatorAgent: Specialized in domain-specific translation
- RegionalReviewerAgent: Applies regional/cultural adjustments
- QualityAgent: Evaluates translation quality and decides if human review is needed
"""

from translation_hub.core.agents.quality_agent import QualityAgent
from translation_hub.core.agents.regional_reviewer_agent import RegionalReviewerAgent
from translation_hub.core.agents.translator_agent import TranslatorAgent

__all__ = ["QualityAgent", "RegionalReviewerAgent", "TranslatorAgent"]
