# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TranslationTask(Document):
	pass


@frappe.whitelist()
def save_translation(task_name: str) -> dict:
	"""
	Save the translation (corrected or AI suggested) to the database.
	Marks the task as Completed.
	
	Args:
		task_name: Name of the Translation Task
		
	Returns:
		dict with success status and message
	"""
	task = frappe.get_doc("Translation Task", task_name)
	
	# Determine which translation to use
	translation = task.corrected_translation or task.suggested_translation
	
	if not translation:
		frappe.throw("No translation available. Please enter a corrected translation.")
	
	if not task.source_text:
		frappe.throw("Source text is missing.")
	
	if not task.target_language:
		frappe.throw("Target language is missing.")
	
	# Save to Translation DocType (Frappe's built-in)
	existing = frappe.db.exists("Translation", {
		"source_text": task.source_text,
		"language": task.target_language
	})
	
	if existing:
		# Update existing translation
		frappe.db.set_value("Translation", existing, "translated_text", translation)
		action = "updated"
	else:
		# Create new translation
		trans_doc = frappe.get_doc({
			"doctype": "Translation",
			"source_text": task.source_text,
			"translated_text": translation,
			"language": task.target_language,
		})
		trans_doc.insert(ignore_permissions=True)
		action = "created"
	
	# Mark task as completed
	task.status = "Completed"
	task.save(ignore_permissions=True)
	
	# Clear translation cache for this language
	frappe.cache.delete_value(f"lang_translation:{task.target_language}")
	
	frappe.db.commit()
	
	return {
		"success": True,
		"message": f"Translation {action} successfully! Task marked as Completed.",
		"action": action
	}


@frappe.whitelist()
def request_retranslation(task_name: str) -> dict:
	"""
	Request a new AI translation considering the rejection reason.
	
	Args:
		task_name: Name of the Translation Task
		
	Returns:
		dict with the new suggested translation
	"""
	task = frappe.get_doc("Translation Task", task_name)
	settings = frappe.get_single("Translator Settings")
	
	if not task.source_text:
		frappe.throw("Source text is missing.")
	
	if not task.target_language:
		frappe.throw("Target language is missing.")
	
	# Build prompt with rejection context
	rejection_context = task.rejection_reason or "Quality check failed"
	previous_translation = task.suggested_translation or ""
	
	prompt = f"""You are a professional translator specialized in ERP/business software.
You need to CORRECT a translation that was rejected.

SOURCE TEXT: {task.source_text}
TARGET LANGUAGE: {task.target_language}

PREVIOUS TRANSLATION (REJECTED): {previous_translation}

REJECTION REASON: {rejection_context}

CRITICAL RULES:
1. Keep ALL placeholders EXACTLY as they appear in the source:
   - Empty: {{}} and #{{}} must remain as {{}} and #{{}}
   - Numbered: {{0}}, {{1}}, #{{0}} must NOT be changed
   - DO NOT add numbers to empty placeholders
2. Keep HTML tags intact
3. FIX the specific issue mentioned in the rejection reason
4. Use appropriate business/ERP terminology

Respond with ONLY the corrected translation, nothing else."""

	try:
		# Get LLM provider configuration
		llm_provider = settings.llm_provider or "Gemini"
		
		if llm_provider == "Gemini":
			import google.generativeai as genai
			
			api_key = settings.get_password("api_key")
			genai.configure(api_key=api_key)
			model = genai.GenerativeModel(settings.gemini_model or "gemini-2.0-flash")
			response = model.generate_content(prompt)
			new_translation = response.text.strip()
			
		elif llm_provider in ("Groq", "OpenRouter"):
			from openai import OpenAI
			
			if llm_provider == "Groq":
				api_key = settings.get_password("groq_api_key")
				base_url = "https://api.groq.com/openai/v1"
				model_name = settings.groq_model or "llama-3.3-70b-versatile"
			else:
				api_key = settings.get_password("openrouter_api_key")
				base_url = "https://openrouter.ai/api/v1"
				model_name = settings.openrouter_model or "deepseek/deepseek-chat-v3-0324:free"
			
			client = OpenAI(api_key=api_key, base_url=base_url)
			response = client.chat.completions.create(
				model=model_name,
				messages=[{"role": "user", "content": prompt}],
				temperature=0.3,
			)
			new_translation = response.choices[0].message.content.strip()
		else:
			frappe.throw(f"Unknown LLM provider: {llm_provider}")
		
		# Update the suggested translation
		task.suggested_translation = new_translation
		task.corrected_translation = new_translation  # Pre-fill corrected field
		
		# Auto-evaluate with QualityAgent
		quality_result = evaluate_translation_quality(
			task.source_text, 
			new_translation, 
			settings.quality_threshold or 0.8
		)
		
		if quality_result["passed"]:
			# Auto-approve: save translation and mark as completed
			_save_translation_to_db(task, new_translation)
			task.status = "Completed"
			task.save(ignore_permissions=True)
			
			return {
				"success": True,
				"new_translation": new_translation,
				"auto_approved": True,
				"quality_score": quality_result["score"],
				"message": f"✅ AI generated a new translation (score: {quality_result['score']:.2f}) and it was AUTO-APPROVED!"
			}
		else:
			# Still needs review
			task.save(ignore_permissions=True)
			
			return {
				"success": True,
				"new_translation": new_translation,
				"auto_approved": False,
				"quality_score": quality_result["score"],
				"quality_issues": quality_result["issues"],
				"message": f"AI generated a new translation (score: {quality_result['score']:.2f}). Still needs review: {', '.join(quality_result['issues'])}"
			}
		
	except Exception as e:
		frappe.log_error(f"Retranslation failed: {e}", "Translation Task Retranslation")
		return {
			"success": False,
			"message": f"Failed to generate new translation: {str(e)}"
		}


def evaluate_translation_quality(source: str, translation: str, threshold: float) -> dict:
	"""
	Evaluate translation quality using the same checks as QualityAgent.
	
	Returns:
		dict with 'passed', 'score', and 'issues'
	"""
	import re
	
	issues = []
	min_score = 1.0
	
	# Check placeholders
	placeholder_patterns = [
		r"\{\}",  # {} empty
		r"#\{\}",  # #{} 
		r"\{[0-9]+\}",  # {0}, {1}
		r"#\{[0-9]+\}",  # #{0}
		r"\{[a-zA-Z_][a-zA-Z0-9_]*\}",  # {name}
		r"%[sd]",  # %s, %d
		r"%\([a-zA-Z_][a-zA-Z0-9_]*\)[sd]",  # %(name)s
	]
	
	for pattern in placeholder_patterns:
		source_matches = set(re.findall(pattern, source))
		trans_matches = set(re.findall(pattern, translation))
		
		missing = source_matches - trans_matches
		extra = trans_matches - source_matches
		
		if missing:
			issues.append(f"Missing placeholders: {missing}")
			min_score = min(min_score, 0.3)
		if extra:
			issues.append(f"Extra placeholders: {extra}")
			min_score = min(min_score, 0.3)
	
	# Check HTML tags
	tag_pattern = r"<[^>]+>"
	source_tags = re.findall(tag_pattern, source)
	trans_tags = re.findall(tag_pattern, translation)
	
	if len(source_tags) != len(trans_tags):
		issues.append(f"HTML tag count mismatch: {len(source_tags)} vs {len(trans_tags)}")
		min_score = min(min_score, 0.5)
	
	# Check length ratio
	if source and translation:
		ratio = len(translation) / len(source)
		if ratio < 0.3:
			issues.append(f"Translation too short (ratio: {ratio:.2f})")
			min_score = min(min_score, 0.6)
		elif ratio > 3.0:
			issues.append(f"Translation too long (ratio: {ratio:.2f})")
			min_score = min(min_score, 0.6)
	
	# Check empty
	if source and not translation.strip():
		issues.append("Translation is empty")
		min_score = 0.0
	
	return {
		"passed": min_score >= threshold,
		"score": min_score,
		"issues": issues
	}


def _save_translation_to_db(task, translation: str):
	"""Save translation to Frappe's Translation DocType."""
	existing = frappe.db.exists("Translation", {
		"source_text": task.source_text,
		"language": task.target_language
	})
	
	if existing:
		frappe.db.set_value("Translation", existing, "translated_text", translation)
	else:
		trans_doc = frappe.get_doc({
			"doctype": "Translation",
			"source_text": task.source_text,
			"translated_text": translation,
			"language": task.target_language,
		})
		trans_doc.insert(ignore_permissions=True)
	
	# Clear cache
	frappe.cache.delete_value(f"lang_translation:{task.target_language}")
