import polib
import logging
from pathlib import Path
from typing import List, Optional


class TranslationFile:
    """
    Encapsulates the manipulation of a .po file, handling loading, merging,
    and saving operations using the polib library.
    """

    def __init__(self, po_path: Path, pot_path: Optional[Path] = None, logger: Optional[logging.Logger] = None):
        """
        Initializes the TranslationFile instance.

        Args:
            po_path: Path to the .po file.
            pot_path: Optional path to the .pot template file for merging.
            logger: Optional logger instance.
        """
        self.po_path = po_path
        self.pot_path = pot_path
        self.logger = logger or logging.getLogger(__name__)
        self.pofile: polib.POFile = self._load_or_create_pofile()

    def _load_or_create_pofile(self) -> polib.POFile:
        """
        Loads an existing .po file or creates a new one if it doesn't exist.
        If a .pot file is provided, it's used as a template for a new file.
        """
        if self.po_path.exists():
            self.logger.info(f"Loading existing .po file from: {self.po_path}")
            return polib.pofile(str(self.po_path), encoding="utf-8")

        self.logger.info(f"Creating new .po file at: {self.po_path}")
        pofile = polib.POFile(wrapwidth=0)  # Disable line wrapping for cleaner git diffs

        if self.pot_path and self.pot_path.exists():
            potfile = polib.pofile(str(self.pot_path), encoding="utf-8")
            pofile.metadata = potfile.metadata

        return pofile

    def merge(self):
        """
        Merges the .pot file into the .po file. This adds new entries from
        .pot and marks entries in .po that are not in .pot as obsolete.
        """
        if not self.pot_path or not self.pot_path.exists():
            self.logger.warning("[Warning] .pot file not found. Skipping merge.")
            return

        self.logger.info(f"Loading .pot file from: {self.pot_path}")
        potfile = polib.pofile(str(self.pot_path), encoding="utf-8")

        self.logger.info(f"Merging entries from {self.pot_path} into {self.po_path}...")
        self.pofile.merge(potfile)
        self.logger.info(f"Total entries after merge: {len(self.pofile)}")
        self.save()  # Save to reflect the merge immediately

    def get_untranslated_entries(self) -> List[dict]:
        """
        Filters and returns a list of entries that are untranslated or marked as fuzzy.
        Each entry is a dictionary containing the msgid and its context.
        """
        untranslated_entries = [
            entry for entry in self.pofile if not entry.msgstr or "fuzzy" in entry.flags
        ]
        self.logger.info(f"Found {len(untranslated_entries)} entries to translate.")

        return [
            {
                "msgid": entry.msgid,
                "context": {
                    "occurrences": entry.occurrences,
                    "comment": entry.comment,
                    "tcomment": entry.tcomment,
                    "flags": entry.flags,
                },
            }
            for entry in untranslated_entries
        ]

    def update_entries(self, translated_entries: List[dict]):
        """
        Updates the current pofile in memory with new translations.
        """
        for translated_entry in translated_entries:
            entry = self.pofile.find(translated_entry["msgid"])
            if entry:
                entry.msgstr = translated_entry["msgstr"]
                # Clear the 'fuzzy' flag if it was present
                if "fuzzy" in entry.flags:
                    entry.flags.remove("fuzzy")

    def save(self):
        """
        Saves the .po file to disk.
        """
        self.logger.info(f"Saving translated .po file to: {self.po_path}")
        self.pofile.save(str(self.po_path))

    def final_verification(self):
        """
        Performs a final check to see if any entries are still untranslated.
        """
        final_untranslated = [entry for entry in self.pofile if not entry.msgstr or "fuzzy" in entry.flags]
        if final_untranslated:
            self.logger.warning("\n[WARNING] Some entries still do not have a translation (msgstr is empty or marked as fuzzy):")
            for entry in final_untranslated:
                occurrence = (
                    f" (Source: {entry.occurrences[0][0]}:{entry.occurrences[0][1]})" if entry.occurrences else ""
                )
                self.logger.warning(f"  - msgid: '{entry.msgid}'{occurrence}")
        else:
            self.logger.info("\nAll entries in the .po file have a translation (msgstr is not empty).")
