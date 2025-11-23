from pathlib import Path
from unittest.mock import MagicMock

import polib

from translation_hub.core.translation_file import TranslationFile

# Sample .pot content
POT_CONTENT = """
#. Translators:
msgid ""
msgstr ""
"Project-Id-Version: ERPNext 1.0\\n"
"POT-Creation-Date: 2025-01-01 12:00+0000\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

msgid "Hello"
msgstr ""

msgid "World"
msgstr ""

msgid "To be merged"
msgstr ""
"""

# Sample .po content for loading
PO_CONTENT = """
msgid "Hello"
msgstr "Olá"

msgid "World"
msgstr ""

# This entry is fuzzy
#, fuzzy
msgid "Fuzzy"
msgstr "Fuzzy"

msgid "Empty"
msgstr ""
"""


def test_create_new_po_file(tmp_path: Path):
	"""
	Tests that a new .po file is created if it doesn't exist.
	"""
	po_path = tmp_path / "new.po"
	mock_logger = MagicMock()
	t_file = TranslationFile(po_path=po_path, logger=mock_logger)

	assert t_file.pofile is not None
	assert len(t_file.pofile) == 0
	t_file.save()
	assert po_path.exists()


def test_load_existing_po_file(tmp_path: Path):
	"""
	Tests that an existing .po file is loaded correctly.
	"""
	po_path = tmp_path / "existing.po"
	po_path.write_text(PO_CONTENT, encoding="utf-8")

	mock_logger = MagicMock()
	t_file = TranslationFile(po_path=po_path, logger=mock_logger)
	# polib counts the metadata entry, so we expect 3 entries + metadata = 4
	assert len(t_file.pofile) == 4
	assert t_file.pofile.find("Hello").msgstr == "Olá"


def test_merge_from_pot_file(tmp_path: Path):
	"""
	Tests that new entries from a .pot file are merged into the .po file.
	"""
	pot_path = tmp_path / "template.pot"
	pot_path.write_text(POT_CONTENT, encoding="utf-8")

	po_path = tmp_path / "output.po"
	po_path.write_text(PO_CONTENT, encoding="utf-8")

	mock_logger = MagicMock()
	t_file = TranslationFile(po_path=po_path, pot_path=pot_path, logger=mock_logger)
	t_file.merge()

	# "To be merged" should be added. "Fuzzy" and "Empty" should be removed as they are not in the pot file.
	assert t_file.pofile.find("To be merged") is not None
	assert t_file.pofile.find("Fuzzy") is None
	assert t_file.pofile.find("Empty") is None
	assert t_file.pofile.find("Hello") is not None
	assert t_file.pofile.find("World") is not None


def test_get_untranslated_entries(tmp_path: Path):
	"""
	Tests that it correctly identifies untranslated and fuzzy entries.
	"""
	po_path = tmp_path / "test.po"
	po_path.write_text(PO_CONTENT, encoding="utf-8")

	mock_logger = MagicMock()
	t_file = TranslationFile(po_path=po_path, logger=mock_logger)
	untranslated = t_file.get_untranslated_entries()

	assert len(untranslated) == 3  # "World" (empty), "Fuzzy" (fuzzy), and "Empty" (empty)
	msgids = {entry["msgid"] for entry in untranslated}
	assert "World" in msgids
	assert "Fuzzy" in msgids
	assert "Empty" in msgids
	# Check the structure of the first entry
	world_entry = next(entry for entry in untranslated if entry["msgid"] == "World")
	assert "context" in world_entry
	assert "occurrences" in world_entry["context"]


def test_update_entries(tmp_path: Path):
	"""
	Tests that entries are correctly updated with new translations.
	"""
	po_path = tmp_path / "test.po"
	po_path.write_text(PO_CONTENT, encoding="utf-8")

	mock_logger = MagicMock()
	t_file = TranslationFile(po_path=po_path, logger=mock_logger)

	# Create mock translated entries
	translated_entries = [
		{"msgid": "World", "msgstr": "Mundo"},
		{"msgid": "Fuzzy", "msgstr": "Não Difuso"},
	]

	t_file.update_entries(translated_entries)

	world_entry = t_file.pofile.find("World")
	fuzzy_entry = t_file.pofile.find("Fuzzy")

	assert world_entry.msgstr == "Mundo"
	assert fuzzy_entry.msgstr == "Não Difuso"
	assert "fuzzy" not in fuzzy_entry.flags


def test_final_verification(tmp_path: Path, caplog):
	"""
	Tests the final verification method's output.
	"""
	po_path = tmp_path / "test.po"
	po_path.write_text(PO_CONTENT, encoding="utf-8")

	t_file = TranslationFile(po_path=po_path)

	# Simulate partial translation
	entry_to_translate = t_file.pofile.find("World")
	entry_to_translate.msgstr = "Mundo"

	with caplog.at_level("WARNING"):
		t_file.final_verification()

	assert "Some entries still do not have a translation" in caplog.text
	assert "msgid: 'World'" not in caplog.text
	assert "msgid: 'Fuzzy'" in caplog.text
	assert "msgid: 'Empty'" in caplog.text
