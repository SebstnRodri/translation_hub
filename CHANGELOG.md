# Changelog

All notable changes to this project will be documented in this file.

## [v1.1.2-beta] - 2025-12-06

### 🚀 Features
- **Workspace**: Redesigned Translation Hub workspace with "Setup & Configuration" section for improved navigation.

### 🐛 Bug Fixes
- **Bench Update**: Fixed `ValueError: unconverted data remains` during `bench update` by removing microseconds from `POT-Creation-Date` and `PO-Revision-Date` headers in PO files and generation logic.

---

## [v1.1.1-beta] - 2025-12-04


### 🛠️ Improvements
- **Release Automation**:
    - Added automated release script (`scripts/release.sh`) to ensure version consistency
    - Created comprehensive release process documentation
    - Prevents version file mismatches in future releases

---

## [v1.1.0-beta] - 2025-12-04


### 🚀 Features
- **Git-Based Backup & Restore**:
    - **GitSyncService**: New service for managing translation backups via Git repositories
    - **Repository Structure**: Organizes backups by app (`app_name/locale/*.po`)
    - **Authentication**: Supports Personal Access Tokens (PAT) for private repositories
    - **Manual Controls**: UI buttons for manual backup and restore operations
    - **Automated Backups**: Configurable schedule (None/Daily/Weekly)
    - **Storage Location**: `sites/[site_name]/private/translation_backup_repo`
- **Translator Settings Enhancements**:
    - Added backup configuration section (repo URL, branch, auth token, frequency)
    - Automatic duplicate removal for monitored apps and languages
    - Improved validation logic

### 🐛 Bug Fixes
- **Pre-commit Hook**: Removed problematic `cleanup-test-files` hook that caused commit failures
- **Test Isolation**: Added `*_test.po` to `.gitignore` instead of deleting during commits
- **Auth Token**: Made auth_token optional in GitSyncService for local repositories

### 🧪 Testing
- **GitSyncService Tests**: Comprehensive test suite with 4 tests covering:
    - Backup directory structure creation
    - Restore functionality
    - No-changes handling
    - Multiple apps support

### 📚 Documentation
- Updated `architecture.md` with GitSyncService component and backup flow
- Added backup/restore section to `getting_started.md`
- Updated README.md with Git-based backup feature

---

## [v1.0.0-beta] - 2025-11-27


### 🚀 Features
- **Automated Workflow**:
    - **Self-Healing**: Automatically generates `main.pot` template files if missing (`ensure_pot_file`).
    - **Real-Time Sync**: Automatically merges new translations into `.po` files (`TranslationFile.merge`).
    - **Smart Triggers**: Automated translations run automatically when `Translator Settings` are saved.
- **Governance**:
    - **Unique Job Naming**: Jobs now use timestamped names (`Automated: {app} - {lang} - {timestamp}`) to prevent `DuplicateEntryError`.
    - **Validation**: Enforces that jobs match configured App/Language pairs.
- **Data Integrity**:
    - **HTML Preservation**: Disabled destructive database export to protect HTML tags in translations.
    - **Safe Storage**: Prioritizes real-time file saving (`save_to_po_file`) over database dumps.

### 🐛 Bug Fixes
- **Security**: Masked API keys in logs to prevent sensitive data exposure.
- **Path Handling**: Fixed `AttributeError` by ensuring `pathlib.Path` objects are used consistently.
- **Empty PO Files**: Fixed issue where new PO files were created empty by forcing a merge with the POT template.
- **Log Noise**: Removed misleading "Checking API Key for Mock Service" log message.

### 📚 Documentation
- Added compatibility note for **Frappe Framework v16.0.0-dev**.

---

## [v0.2.1] - 2025-11-26

### ⚡ Improvements
- **Automated POT Generation**: Removed the need for manual `bench generate-pot-file` commands.

---

## [v0.2.0] - 2025-11-26

### ✨ New Features
- **Multi-Language Support**: Configure a single "Monitored App" to target multiple languages automatically.
- **Standardization Guides**:
    - **System Guide**: Global instructions for all translations.
    - **App Guide**: Specific instructions for each App.
    - **Language Guide**: Specific instructions for each Language (e.g., "Use formal 'Você'").
- **Composite Prompting**: The AI now receives a combined guide (System + App + Language) for higher context awareness.
