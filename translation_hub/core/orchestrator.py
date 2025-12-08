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
