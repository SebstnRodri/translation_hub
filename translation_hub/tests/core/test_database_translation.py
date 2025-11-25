import pytest
import frappe
from translation_hub.core.database_translation import DatabaseTranslationHandler


@pytest.fixture
def cleanup_translations():
	"""Clean up test translations after each test"""
	yield
	# Delete all test translations
	frappe.db.delete("Translation", {"language": "test_lang"})
	frappe.db.commit()


def test_save_single_translation(cleanup_translations):
	"""Test saving a single translation to database"""
	handler = DatabaseTranslationHandler("test_lang")
	
	entries = [
		{"msgid": "Hello", "msgstr": "Hola"}
	]
	
	count = handler.save_translations(entries)
	
	assert count == 1
	
	# Verify in database
	translation = frappe.db.get_value(
		"Translation",
		{"source_text": "Hello", "language": "test_lang"},
		["translated_text"],
		as_dict=True
	)
	assert translation["translated_text"] == "Hola"


def test_save_multiple_translations(cleanup_translations):
	"""Test saving multiple translations"""
	handler = DatabaseTranslationHandler("test_lang")
	
	entries = [
		{"msgid": "Hello", "msgstr": "Hola"},
		{"msgid": "World", "msgstr": "Mundo"},
		{"msgid": "Goodbye", "msgstr": "Adiós"},
	]
	
	count = handler.save_translations(entries)
	
	assert count == 3
	
	# Verify all translations
	translations = handler.get_all_translations()
	assert len(translations) == 3


def test_update_existing_translation(cleanup_translations):
	"""Test updating an existing translation"""
	handler = DatabaseTranslationHandler("test_lang")
	
	# Save initial translation
	handler.save_translations([{"msgid": "Hello", "msgstr": "Hola"}])
	
	# Update with new translation
	handler.save_translations([{"msgid": "Hello", "msgstr": "¡Hola!"}])
	
	# Verify updated
	translation = frappe.db.get_value(
		"Translation",
		{"source_text": "Hello", "language": "test_lang"},
		["translated_text"],
		as_dict=True
	)
	assert translation["translated_text"] == "¡Hola!"
	
	# Should still be only 1 translation (not 2)
	translations = handler.get_all_translations()
	assert len(translations) == 1


def test_skip_failed_translations(cleanup_translations):
	"""Test that failed translations are skipped"""
	handler = DatabaseTranslationHandler("test_lang")
	
	entries = [
		{"msgid": "Hello", "msgstr": "Hola"},
		{"msgid": "Failed", "msgstr": "[TRANSLATION_FAILED] Failed"},
		{"msgid": "World", "msgstr": "Mundo"},
	]
	
	count = handler.save_translations(entries)
	
	# Should only save 2 (skip the failed one)
	assert count == 2
	
	translations = handler.get_all_translations()
	assert len(translations) == 2


def test_translation_with_context(cleanup_translations):
	"""Test saving translations with context"""
	handler = DatabaseTranslationHandler("test_lang")
	
	entries = [
		{"msgid": "Save", "msgstr": "Guardar", "context": "button"},
		{"msgid": "Save", "msgstr": "Ahorrar", "context": "money"},
	]
	
	count = handler.save_translations(entries)
	
	assert count == 2
	
	# Verify both translations exist with different contexts
	button_translation = frappe.db.get_value(
		"Translation",
		{"source_text": "Save", "language": "test_lang", "context": "button"},
		["translated_text"],
		as_dict=True
	)
	assert button_translation["translated_text"] == "Guardar"
	
	money_translation = frappe.db.get_value(
		"Translation",
		{"source_text": "Save", "language": "test_lang", "context": "money"},
		["translated_text"],
		as_dict=True
	)
	assert money_translation["translated_text"] == "Ahorrar"


def test_get_all_translations(cleanup_translations):
	"""Test retrieving all translations for a language"""
	handler = DatabaseTranslationHandler("test_lang")
	
	entries = [
		{"msgid": "One", "msgstr": "Uno"},
		{"msgid": "Two", "msgstr": "Dos"},
		{"msgid": "Three", "msgstr": "Tres"},
	]
	
	handler.save_translations(entries)
	
	translations = handler.get_all_translations()
	
	assert len(translations) == 3
	assert all("source_text" in t for t in translations)
	assert all("translated_text" in t for t in translations)


def test_export_to_po(cleanup_translations, tmp_path):
	"""Test exporting database translations to .po file"""
	import polib
	
	handler = DatabaseTranslationHandler("test_lang")
	
	entries = [
		{"msgid": "Hello", "msgstr": "Hola"},
		{"msgid": "World", "msgstr": "Mundo"},
	]
	
	handler.save_translations(entries)
	
	# Export to .po file
	po_file = tmp_path / "test.po"
	handler.export_to_po(str(po_file))
	
	# Verify .po file was created
	assert po_file.exists()
	
	# Verify .po file contents
	po = polib.pofile(str(po_file))
	assert len(po) == 2
	
	# Find entries
	hello_entry = next((e for e in po if e.msgid == "Hello"), None)
	assert hello_entry is not None
	assert hello_entry.msgstr == "Hola"
