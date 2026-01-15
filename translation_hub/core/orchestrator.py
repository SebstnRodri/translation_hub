import logging
import sys
from collections.abc import Generator

import polib

from translation_hub.core.config import TranslationConfig
from translation_hub.core.translation_file import TranslationFile
from translation_hub.core.translation_service import TranslationService


class TranslationOrchestrator:
	"""
	Orchestrates the translation process by coordinating the TranslationFile
	and a TranslationService.
	"""

	def __init__(
		self,
		config: TranslationConfig,
		file_handler: TranslationFile,
		service: TranslationService,
		logger: logging.Logger,
	):
		self.config = config
		self.file_handler = file_handler
		self.service = service
		self.logger = logger

	def run(self):
		"""
		Executes the main translation workflow.
		"""
		try:
			self.file_handler.merge()

			# REUSE EXISTING TRANSLATIONS FROM DB
			# If database storage is enabled, pull known translations from DB into the PO file
			# before we check for untranslated entries. This prevents re-translating known strings.
			if self.config.use_database_storage:
				from translation_hub.core.database_translation import DatabaseTranslationHandler

				self.logger.info("Syncing existing translations from database...")
				db_handler = DatabaseTranslationHandler(self.config.language_code, self.logger)
				# This updates the PO file on disk with any matching source_text from DB
				db_handler.export_to_po(str(self.config.po_file))
				# Reload the file handler to pick up changes from disk
				self.file_handler.reload()

			untranslated_entries = self.file_handler.get_untranslated_entries()
			total_strings = len(untranslated_entries)
			translated_strings = 0
			self.logger.update_progress(translated_strings, total_strings)

			if not untranslated_entries:
				self.logger.info("All entries are already translated. Nothing to do.")
				self.file_handler.save()  # Save to ensure metadata is correct
				return

			batches = list(self._split_into_batches(untranslated_entries, self.config.batch_size))
			total_batches = len(batches)
			self.logger.info(f"Created {total_batches} batches of size {self.config.batch_size}.")

			# === AGENT PIPELINE MODE ===
			if self.config.use_agent_pipeline:
				self._run_agent_pipeline(untranslated_entries, total_strings)
				return

			for i, batch in enumerate(batches):
				self.logger.info(f"--- Translating batch {i + 1}/{total_batches} ---")

				translated_batch = self.service.translate(batch)
				# Filter out None results (failed translations are skipped)
				translated_batch = [entry for entry in translated_batch if entry is not None]
				translated_strings += len(translated_batch)
				self.logger.update_progress(translated_strings, total_strings)

				for entry in translated_batch:
					self.logger.debug(f"  - Original: {entry['msgid']}")
					self.logger.debug(f"    Translation: {entry['msgstr']}")

				# Save to database (PRIMARY STORAGE)
				if self.config.use_database_storage:
					from translation_hub.core.database_translation import DatabaseTranslationHandler

					db_handler = DatabaseTranslationHandler(self.config.language_code, self.logger)
					db_handler.save_translations(translated_batch)

				# OPTIONAL: Also save to .po file
				if self.config.save_to_po_file:
					self.file_handler.update_entries(translated_batch)
					self.file_handler.save()

				self.logger.info(f"--- Batch {i + 1}/{total_batches} saved ---")

			self.logger.info("\nTranslation complete!")

			# OPTIONAL: Export database to .po file at completion
			if self.config.use_database_storage and self.config.export_po_on_complete:
				from translation_hub.core.database_translation import DatabaseTranslationHandler

				db_handler = DatabaseTranslationHandler(self.config.language_code, self.logger)
				db_handler.export_to_po(str(self.config.po_file))
				self.logger.info(f"Exported database translations to {self.config.po_file}")

			self.file_handler.final_verification()

		except KeyboardInterrupt:
			self.logger.warning("\n\nProcess interrupted by user.")
			self.logger.warning(
				f"Translations completed up to the last batch have been saved in: {self.file_handler.po_path}"
			)
			self.logger.warning("To continue, simply run the command again.")
			sys.exit(130)

	def _run_agent_pipeline(self, untranslated_entries: list, total_strings: int):
		"""
		Run the multi-agent translation pipeline.
		Quality > Economy: Uses 3 LLM calls per batch.
		No automatic fallback: Pauses for inspection on failure.
		"""
		from translation_hub.core.agent_orchestrator import AgentOrchestrator, create_review_from_result

		self.logger.info("=== AGENT PIPELINE MODE ===")
		self.logger.info("Pipeline: TranslatorAgent → RegionalReviewerAgent → QualityAgent")

		# Determine app_name from context if possible
		app_name = getattr(self.config, "app_name", None)
		regional_profile = self.config.regional_expert_profile
		self.logger.info(f"Regional Expert Profile: '{regional_profile}'")

		agent_orchestrator = AgentOrchestrator(
			config=self.config,
			app_name=app_name,
			regional_profile=regional_profile,
			logger=self.logger,
		)

		# Process in batches
		batches = list(self._split_into_batches(untranslated_entries, self.config.batch_size))
		total_batches = len(batches)
		translated_strings = 0
		reviews_created = 0

		for i, batch in enumerate(batches):
			self.logger.info(f"--- Agent Pipeline Batch {i + 1}/{total_batches} ---")

			# Convert POEntry to dict for the agent pipeline
			batch_dicts = [
				{
					"msgid": entry.msgid if hasattr(entry, "msgid") else entry.get("msgid", ""),
					"msgstr": entry.msgstr if hasattr(entry, "msgstr") else entry.get("msgstr", ""),
					"msgctxt": entry.msgctxt if hasattr(entry, "msgctxt") else entry.get("msgctxt", ""),
					"occurrences": entry.occurrences
					if hasattr(entry, "occurrences")
					else entry.get("occurrences", []),
					"flags": entry.flags if hasattr(entry, "flags") else entry.get("flags", []),
					"comment": entry.comment if hasattr(entry, "comment") else entry.get("comment", ""),
				}
				for entry in batch
			]

			# Run the 3-agent pipeline
			results = agent_orchestrator.translate_with_review(batch_dicts)

			# Process results - accumulate translations for batch saving
			batch_translations = []
			batch_po_entries = []

			for result in results:
				if result.needs_human_review:
					# Create Translation Review for human review
					import frappe

					review_name = create_review_from_result(
						result,
						source_app=app_name or "unknown",
						language=self.config.language_code,
					)
					self.logger.info(
						f"  → Created review {review_name} for '{result.msgid[:30]}...' (score={result.quality_score:.2f})"
					)
					reviews_created += 1
				else:
					# Accumulate high-quality translations for batch saving
					translated_entry = {"msgid": result.msgid, "msgstr": result.msgstr}
					batch_translations.append(translated_entry)

					if self.config.save_to_po_file:
						batch_po_entries.append(translated_entry)

				translated_strings += 1
				self.logger.update_progress(translated_strings, total_strings)

			# Save all batch translations at once (correct log: "Saved X/Y translations")
			if self.config.use_database_storage and batch_translations:
				from translation_hub.core.database_translation import DatabaseTranslationHandler

				db_handler = DatabaseTranslationHandler(self.config.language_code, self.logger)
				db_handler.save_translations(batch_translations)

			if self.config.save_to_po_file and batch_po_entries:
				self.file_handler.update_entries(batch_po_entries)
				self.file_handler.save()

			self.logger.info(f"--- Batch {i + 1}/{total_batches} complete ---")

		# Final summary
		self.logger.info("\n=== AGENT PIPELINE COMPLETE ===")
		self.logger.info(f"Total translated: {translated_strings}")
		self.logger.info(f"Sent to human review: {reviews_created}")
		self.logger.info(f"Auto-approved: {translated_strings - reviews_created}")

		if self.config.use_database_storage and self.config.export_po_on_complete:
			from translation_hub.core.database_translation import DatabaseTranslationHandler

			db_handler = DatabaseTranslationHandler(self.config.language_code, self.logger)
			db_handler.export_to_po(str(self.config.po_file))
			self.logger.info(f"Exported database translations to {self.config.po_file}")

		self.file_handler.final_verification()

	@staticmethod
	def _split_into_batches(
		entries: list[polib.POEntry], batch_size: int
	) -> Generator[list[polib.POEntry], None, None]:
		"""
		Splits a list of entries (dictionaries) into batches of a given size.
		"""
		if not entries:
			return
		for i in range(0, len(entries), batch_size):
			yield entries[i : i + batch_size]
