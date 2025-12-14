# Changelog

All notable changes to Translation Hub will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.1] - 2024-12-14

### Fixed
- **API Key Retrieval**: Fixed bug where Translation Job failed when using Groq/OpenRouter by removing premature api_key retrieval
  - Moved Gemini API key retrieval to conditional block
  - Each provider now fetches only its own API key
  - File: [tasks.py](file:///home/ubuntu/Project/frappe-v16/apps/translation_hub/translation_hub/tasks.py#L107-L111)

- **Translation Review Creation**: Fixed mandatory field error when creating reviews for untranslated strings
  - Added fallback to use source_text when current_translation is empty
  - Prevents empty suggested_text field validation error
  - File: [translation_review.py](file:///home/ubuntu/Project/frappe-v16/apps/translation_hub/translation_hub/translation_hub/doctype/translation_review/translation_review.py#L118-L120)

- **PO to Database Import**: Added automatic import of .po files to Translation database after restore
  - Implemented `_import_to_database()` method in GitSyncService
  - Translation Review now works correctly with restored translations
  - Uses polib to parse .po files and populate tabTranslation
  - File: [git_sync_service.py](file:///home/ubuntu/Project/frappe-v16/apps/translation_hub/translation_hub/core/git_sync_service.py#L227-L304)

- **Compilation Method**: Corrected translation compilation to use proper Frappe API
  - Changed from non-existent `frappe.translate.build_message_files()`
  - To correct `frappe.gettext.translate.compile_translations()`
  - Files: [git_sync_service.py](file:///home/ubuntu/Project/frappe-v16/apps/translation_hub/translation_hub/core/git_sync_service.py#L310), [tasks.py](file:///home/ubuntu/Project/frappe-v16/apps/translation_hub/translation_hub/tasks.py#L181)

### Technical Details
**Files Modified:**
- `translation_hub/__init__.py` - Version 1.6.1
- `translation_hub/hooks.py` - Version 1.6.1
- `translation_hub/tasks.py` - API key retrieval fix, compilation fix
- `translation_hub/doctype/translation_review/translation_review.py` - Mandatory field fix
- `translation_hub/core/git_sync_service.py` - PO import, compilation fix

## [1.6.0] - 2024-12-14

### Added
- **Language Manager UI**: New user-friendly interface in Translator Settings to enable/disable languages
  - Auto-detects .po files and creates Language records automatically
  - Displays proper language names (e.g., "Português (Brasil)" instead of "PT (BR)")
  - Table view showing ~100+ languages with checkboxes
  - "Load All Languages" button to sync .po files with Language DocType
  - "Save Language Settings" button to persist changes
  - Created `Language Setup Item` child DocType for table display

- **Selective Language Backup**: Backup/restore operations now filter by enabled languages only
  - Added `_get_enabled_language_codes()` helper method in `GitSyncService`
  - Modified `collect_translations()` to only backup enabled languages
  - Modified `distribute_translations()` to only restore enabled languages
  - Significantly reduces repository size for Git backups
  - Provides clearer version control with only relevant translations

- **Locale Directory Cleanup**: New cleanup feature to remove disabled language files
  - "Cleanup Locale Directories" button in Language Manager
  - Removes .po files of disabled languages from monitored apps
  - Confirmation dialog with warning before deletion
  - System Manager permission required
  - Detailed logging and reporting of deleted files
  - Preserves _test.po files automatically

- **Automatic MO Compilation**: Translations are automatically compiled after operations
  - Compiles .po to .mo files after restore operations
  - Compiles after Translation Job completion
  - Uses Frappe's `build_message_files()` for compilation
  - Translations immediately available without manual `bench build`
  - Added `_compile_translations()` helper method

### Changed
- Updated version from 1.5.0 to 1.6.0
- Enhanced `GitSyncService` with language filtering capabilities
- Improved Translation Job workflow with automatic compilation step
- Updated README with new features in both English and Portuguese

### Technical Details
**Files Created:**
- `translation_hub/doctype/language_setup_item/language_setup_item.json`
- `translation_hub/doctype/language_setup_item/language_setup_item.py`
- `translation_hub/doctype/language_setup_item/__init__.py`

**Files Modified:**
- `translation_hub/__init__.py` - Version update
- `translation_hub/doctype/translator_settings/translator_settings.json` - Language Manager section
- `translation_hub/doctype/translator_settings/translator_settings.py` - 3 new whitelisted methods
- `translation_hub/doctype/translator_settings/translator_settings.js` - Button handlers
- `translation_hub/core/git_sync_service.py` - Filtering and compilation
- `translation_hub/tasks.py` - Cleanup wrapper and compilation

## [1.5.0] - 2024-11-XX

### Added
- AI-Assisted Bulk Review for bad translations
- Individual AI Helper for specific translation suggestions
- Multiple LLM provider support (Gemini, Groq, OpenRouter)
- Test API Connection feature
- Enhanced workspace navigation
- Selective backup & restore functionality
- Standard repository workflow integration
- Sync before translate feature

## [1.0.0] - Initial Release

### Added
- Core translation engine with AI support
- Translation Jobs system
- Database storage for translations
- Context-aware translation with standardization guides
- Real-time monitoring dashboard
