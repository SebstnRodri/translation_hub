# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TranslationReview(Document):
	def on_update(self):
		"""
		Called after the document is saved.
		If status changed to 'Approved', apply the suggested translation.
		"""
		if self.has_value_changed("status") and self.status == "Approved":
			self._apply_approved_translation()

	def _apply_approved_translation(self):
		"""
		Applies the suggested translation to the Translation DocType,
		exports to .po file, and triggers remote backup.
		"""
		# 1. Update Translation DocType in DB
		self._update_translation_doctype()

		# 2. Export to .po file
		self._export_to_po_file()

		# 3. Trigger Git backup (sync to remote)
		self._sync_to_remote()

		# 4. Record reviewer info
		self.reviewed_by = frappe.session.user
		self.reviewed_on = frappe.utils.now_datetime()
		self.db_update()

		frappe.msgprint(f"Translation approved and synced for '{self.source_text[:50]}...'")

	def _update_translation_doctype(self):
		"""Updates the Translation DocType with the suggested text."""
		filters = {
			"source_text": self.source_text,
			"language": self.language,
		}

		existing = frappe.db.get_value("Translation", filters, "name")

		if existing:
			frappe.db.set_value("Translation", existing, "translated_text", self.suggested_text)
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Translation",
					"language": self.language,
					"source_text": self.source_text,
					"translated_text": self.suggested_text,
				}
			)
			doc.insert(ignore_permissions=True)

		frappe.db.commit()

	def _export_to_po_file(self):
		"""Exports the updated translation to the .po file."""
		from pathlib import Path

		from translation_hub.core.database_translation import DatabaseTranslationHandler

		app_path = frappe.get_app_path(self.source_app)
		po_path = Path(app_path) / "locale" / f"{self.language.replace('-', '_')}.po"

		if po_path.exists():
			handler = DatabaseTranslationHandler(self.language)
			handler.export_to_po(str(po_path))

	def _sync_to_remote(self):
		"""Triggers Git backup to sync changes to remote repository."""
		try:
			settings = frappe.get_single("Translator Settings")
			if settings.backup_repo_url:
				from translation_hub.core.git_sync_service import GitSyncService

				service = GitSyncService(settings)
				service.backup(apps=[self.source_app])
		except Exception as e:
			frappe.log_error(f"Failed to sync to remote: {e}", "Translation Review Sync")


@frappe.whitelist()
def create_translation_review(source_text: str, language: str, source_app: str):
	"""
	Creates a Translation Review with pre-filled fields.

	Args:
		source_text: The original English text
		language: Language code (e.g., 'pt-BR')
		source_app: App name (e.g., 'erpnext')

	Returns:
		Name of the created Translation Review document
	"""
	# Get current translation from database
	current_translation = (
		frappe.db.get_value(
			"Translation", {"source_text": source_text, "language": language}, "translated_text"
		)
		or ""
	)

	# Check if a pending review already exists
	existing = frappe.db.exists(
		"Translation Review", {"source_text": source_text, "language": language, "status": "Pending"}
	)

	if existing:
		frappe.throw(f"A pending review already exists for this translation: {existing}")

	# Create the review
	# Use current translation if available, otherwise use source text as placeholder
	suggested_value = current_translation if current_translation else source_text
	
	doc = frappe.get_doc(
		{
			"doctype": "Translation Review",
			"source_text": source_text,
			"translated_text": current_translation,
			"suggested_text": suggested_value,  # Use fallback to avoid empty mandatory field
			"language": language,
			"source_app": source_app,
			"status": "Pending",
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return doc.name


@frappe.whitelist()
def get_translations_for_review(
	source_app: str, language: str, search_text: str | None = None, limit: int = 50
):
	"""
	Gets a list of translations that can be reviewed.

	Args:
		source_app: App name to filter
		language: Language code to filter
		search_text: Text to search in source_text or translated_text
		limit: Maximum number of results

	Returns:
		List of translations with source_text and translated_text
	"""
	filters = {"language": language}

	if search_text:
		filters["source_text"] = ["like", f"%{search_text}%"]
		# Ideally we search both, but frappe.get_all AND logic makes it tricky for OR.
		# But since we just want to find *a* translation, searching source is safer.
		# Alternatively, execute raw SQL for OR condition.

	# If search is complex, use frappe.db.sql
	if search_text:
		translations = frappe.db.sql(
			"""
			SELECT source_text, translated_text
			FROM `tabTranslation`
			WHERE language = %(language)s
			AND (source_text LIKE %(search)s OR translated_text LIKE %(search)s)
			LIMIT %(limit)s
		""",
			{"language": language, "search": f"%{search_text}%", "limit": int(limit)},
			as_dict=True,
		)

		# Fallback: Search in memory (PO files + Cache)
		# This ensures we find strings that are visible in UI but not yet in DB
		from frappe.translate import get_all_translations

		memory_translations = get_all_translations(language)

		existing_sources = {t.source_text for t in translations}
		search_lower = search_text.lower()
		count = len(translations)
		limit = int(limit)

		for source, translated in memory_translations.items():
			if count >= limit:
				break

			if source in existing_sources:
				continue

			# Check match
			if search_lower in source.lower() or (translated and search_lower in translated.lower()):
				translations.append(frappe._dict({"source_text": source, "translated_text": translated}))
				count += 1

	else:
		translations = frappe.get_all(
			"Translation", filters=filters, fields=["source_text", "translated_text"], limit=int(limit)
		)

	return translations


@frappe.whitelist()
def create_bulk_reviews(
	source_app: str,
	language: str,
	search_text: str,
	use_ai: bool = False,
	ai_context: str | None = None,
):
	"""
	Creates Translation Reviews for ALL translations matching the search text.

	Args:
		source_app: App name
		language: Language code
		search_text: Text to search for

	Returns:
		Number of reviews created
	"""
	if not search_text or len(search_text) < 3:
		frappe.throw("Search text must be at least 3 characters")

	# 1. Fetch Candidates (DB + Memory)
	translations = get_translations_for_review(source_app, language, search_text, limit=500)

	count = 0

	# Prepare for AI processing if requested
	ai_suggestions = {}
	if use_ai and translations:
		try:
			from translation_hub.core.config import TranslationConfig
			from translation_hub.core.translation_service import GeminiService, GroqService, OpenRouterService

			settings = frappe.get_single("Translator Settings")
			if not settings.llm_provider:
				frappe.throw("Translator Service is not configured (LLM Provider missing).")

			# Determine API Key based on provider
			api_key = None
			if settings.llm_provider == "Gemini":
				api_key = settings.get_password("api_key")
			elif settings.llm_provider == "Groq":
				api_key = settings.get_password("groq_api_key")
			elif settings.llm_provider == "OpenRouter":
				api_key = settings.get_password("openrouter_api_key")

			if not api_key:
				frappe.throw(f"API Key for {settings.llm_provider} is missing.")

			model = settings.get(f"{settings.llm_provider.lower()}_model") or "gemini-pro"

			config = TranslationConfig(
				language_code=language,
				api_key=api_key,
				model_name=model,
				provider=settings.llm_provider,
				standardization_guide=ai_context,  # Inject user context as guide
			)

			# Select Service
			service_map = {"Gemini": GeminiService, "Groq": GroqService, "OpenRouter": OpenRouterService}
			ServiceClass = service_map.get(settings.llm_provider)
			if not ServiceClass:
				frappe.throw(f"Unsupported provider: {settings.llm_provider}")

			service = ServiceClass(config, app_name=source_app)

			# Batch translate
			# Filter only those that really need translation (though here we review all)
			entries = [
				{"msgid": t.source_text, "context": None} for t in translations
			]  # t.context is not available from get_translations_for_review

			# Call AI (chunking if necessary, but 500 might fit in one go for some models, safeguards in service handles retries)
			# Let's chunk conservatively to 50 just in case
			results = []
			chunk_size = 50
			for i in range(0, len(entries), chunk_size):
				chunk = entries[i : i + chunk_size]
				results.extend(service.translate(chunk))

			# Map back results
			for res in results:
				if res and res.get("msgid"):
					ai_suggestions[res["msgid"]] = res.get("msgstr")

		except Exception as e:
			frappe.log_error(f"AI Bulk Review Failed: {e}")
			frappe.msgprint(f"AI Suggestion failed, falling back to existing texts. Error: {e}")

	for t in translations:
		# Check if exists
		existing = frappe.db.exists(
			"Translation Review", {"source_text": t.source_text, "language": language, "status": "Pending"}
		)

		if not existing:
			# Determine suggested text
			suggested = ai_suggestions.get(t.source_text)

			# Fallback to current translation (or source if none)
			if not suggested:
				suggested = t.translated_text or t.source_text

			doc = frappe.get_doc(
				{
					"doctype": "Translation Review",
					"source_text": t.source_text,
					"translated_text": t.translated_text,
					"suggested_text": suggested,
					"language": language,
					"source_app": source_app,
					"status": "Pending",
				}
			)
			doc.insert(ignore_permissions=True)
			count += 1

	frappe.db.commit()
	return count


@frappe.whitelist()
def get_ai_suggestion(source_text: str, language: str, source_app: str, context: str | None = None) -> str:
	"""
	Generate a single AI suggestion for the given text.
	"""
	try:
		from translation_hub.core.config import TranslationConfig
		from translation_hub.core.translation_service import GeminiService, GroqService, OpenRouterService

		settings = frappe.get_single("Translator Settings")
		if not settings.llm_provider:
			frappe.throw("Translator Service is not configured (LLM Provider missing).")

		# Determine API Key based on provider
		api_key = None
		if settings.llm_provider == "Gemini":
			api_key = settings.get_password("api_key")
		elif settings.llm_provider == "Groq":
			api_key = settings.get_password("groq_api_key")
		elif settings.llm_provider == "OpenRouter":
			api_key = settings.get_password("openrouter_api_key")

		if not api_key:
			frappe.throw(f"API Key for {settings.llm_provider} is missing.")

		model = settings.get(f"{settings.llm_provider.lower()}_model") or "gemini-pro"

		config = TranslationConfig(
			language_code=language,
			api_key=api_key,
			model_name=model,
			provider=settings.llm_provider,
			standardization_guide=context,
		)

		service_map = {"Gemini": GeminiService, "Groq": GroqService, "OpenRouter": OpenRouterService}
		ServiceClass = service_map.get(settings.llm_provider)
		if not ServiceClass:
			frappe.throw(f"Unsupported provider: {settings.llm_provider}")

		service = ServiceClass(config, app_name=source_app)

		# Translate single entry
		entry = {"msgid": source_text, "context": None}
		# Using _translate_single logic via translate method
		result = service.translate([entry])

		if result and result[0] and result[0].get("msgstr"):
			return result[0]["msgstr"]

		return ""

	except Exception as e:
		frappe.log_error(f"AI Suggestion Failed: {e}")
		frappe.throw(f"AI Suggestion failed: {e}")
