# Architecture Guide

This document describes the overall architecture and design principles of the `translation_hub` application.

## Recent Changes (v1.6.x - v1.7.x)

> [!NOTE]
> **Version 1.7.0** (2024-12-18): File reorganization, Maintenance Module, GeminiService fix.
>
> **Version 1.6.1** (2024-12-15): Review Center UI overhaul, AI Feedback Loop, Deep Links, bug fixes.
>
> **Version 1.6.0** (2024-12-14): Major update with Language Manager UI, Selective Backup, Locale Cleanup, and Auto-compilation.

### Key Additions in v1.7.0

1. **File Reorganization** - Moved loose scripts to proper module directories:
   - `import_script.py` → `core/po_importer.py`
   - `maintenance.py` → `core/maintenance.py`
   - `setup_demo_context.py` → `utils/demo_setup.py`
2. **Maintenance Module** (`core/maintenance.py`) - Smart utilities for system health:
   - Cancel stuck translation jobs automatically
   - Fix language code mismatches (pt_BR → pt-BR)
   - Clear translation caches dynamically
   - Sync System Settings with site_config
   - CLI command: `bench maintenance --all`
3. **GeminiService Fix** - Added missing `translate()` and `_configure_model()` methods
4. **PO Importer** (`core/po_importer.py`) - Import .po translations to database without context

### Key Additions in v1.6.1

1. **Review Center Page** - Redesigned split-panel UI for efficient translation review
   - Left panel: Pending reviews list with filters (app, language)
   - Right panel: Detail view with editable translation
   - Keyboard shortcuts: `A` (approve), `R` (reject), `↑`/`↓` (navigate)
2. **Deep Links** - URL parameter support (`?review=TR-000123`) for direct navigation
3. **Translation Learning DocType** - Stores AI feedback for continuous improvement
   - `learning_type`: "General Correction" or "Term Correction"
   - `problematic_term` / `correct_term`: Term-specific rules
4. **AI Feedback Loop** - Term corrections injected as "CRITICAL RULES" in AI prompts
5. **Retry with AI** - Re-request translation with rejection feedback as context

### Key Additions in v1.6.0

1. **Language Manager UI** - New child table `Language Setup Item` for managing languages via Frappe Desk
2. **Selective Language Backup** - GitSyncService now filters by enabled languages
3. **Locale Cleanup** - Remove .po files of disabled languages with confirmation dialog
4. **Automatic MO Compilation** - Compile .po to .mo after restore and Translation Jobs

### Key Fixes in v1.6.1

1. **API Key Retrieval** - Fixed Groq/OpenRouter provider support
2. **Translation Review Creation** - Handle empty translations gracefully
3. **PO to Database Import** - Automatically import restored .po files to tabTranslation
4. **Compilation Method** - Use correct `frappe.gettext.translate.compile_translations()`


## Design Principles

The system is designed following a **Layered Architecture** pattern. This separates concerns into distinct, independent components, making the codebase more modular, testable, and extensible.

The four main layers are:

1.  **Presentation Layer (Frappe UI)**: Handles user interaction through Frappe DocTypes and a custom Desk Page.
2.  **Application Layer (Frappe Backend)**: Manages the business logic, including DocType controllers, background jobs, and the scheduler.
3.  **Core Logic Layer**: Contains the domain-specific logic for the translation process. This layer is independent of the Frappe framework.
4.  **Service & Data Access Layer**: Manages external services (translation API) and filesystem interactions (`.po` files).

## Core Components

### Frappe Components

#### DocTypes

- **`Translator Settings` (Singleton DocType)**: Stores global configuration like API keys, automation settings, and monitored apps.
  - Contains child table `Monitored App` for automated translation configuration
  - Contains child table `Translator Language` for default language settings
  - **NEW in v1.6.0**: Contains child table `Language Setup Item` for Language Manager UI
  - Fields: `api_key`, `groq_api_key`, `openrouter_api_key`, `llm_provider`, `standardization_guide`, `enable_automated_translation`, `frequency`, `monitored_apps`, `language_manager`
  - **Language Manager**: UI for enabling/disabling languages via table interface
  - **Selective Backup**: Only backs up enabled languages to reduce repository size

- **`Translation Job` (Standard DocType)**: Represents a single translation task, tracking its status, progress, timing, and logs.
  - Links to `App` (source application) and `Language` (target language)
  - Tracks progress metrics: `total_strings`, `translated_strings`, `progress_percentage`
  - Records timing: `start_time`, `end_time`
  - Maintains execution log for debugging and monitoring
  - Status values: Pending, Queued, In Progress, Completed, Failed, Cancelled
  - **NEW in v1.6.1**: Automatic .mo compilation after job completion

- **`Translation Review` (Standard DocType)**: Allows users to review and correct translations.
  - Links to `Language` and `source_app`
  - Fields: `source_text`, `translated_text` (current), `suggested_text` (AI or manual suggestion)
  - Status: Pending, Approved, Rejected
  - **AI Integration**: Can generate bulk suggestions for bad translations
  - **Workflow**: Review → Approve → Updates Translation DocType
  - **NEW in v1.7.0**: Deep link support via URL parameter (`?review=TR-000123`)
  - **NEW in v1.7.0**: `rejection_reason` field for AI feedback
  - **NEW in v1.7.0**: Retry with AI action on rejected reviews

- **`Translation Learning` (Standard DocType)**: NEW in v1.7.0 - Stores AI learning data from user feedback.
  - Links to `Language` and `source_app`
  - Fields: `source_text`, `original_translation`, `corrected_translation`
  - **Learning Types**:
    - `General Correction`: Full translation corrections used as few-shot examples
    - `Term Correction`: Specific term mappings with `problematic_term` and `correct_term`
  - **Priority**: Term corrections are injected as "CRITICAL TERM RULES" in AI prompts
  - **Usage**: Automatically fetched by TranslationService to improve future translations

- **`App` (Standard DocType)**: Represents a Frappe/ERPNext application available for translation.
  - Stores `app_name` (Link to `Installed App`) and `app_title` (display name)
  - **Context Configuration**: Stores application-specific context for the LLM:
    - `domain` (e.g., Logistics, Healthcare)
    - `tone` (e.g., Formal, Friendly)
    - `description` (Brief app description)
    - `do_not_translate` (Child table of excluded terms)
  - **Validation**: Ensures only apps actually installed on the site can be registered.
  - Referenced by `Translation Job` and `Monitored App`

- **`App Glossary` (Standard DocType)**: Stores language-specific glossary terms for a specific App.
  - Links to `App` and `Language`
  - Contains child table `Glossary Items` (Term, Translation, Description)
  - Used to inject specific terminology into the translation context.

- **`Language Setup Item` (Child Table)**: NEW in v1.6.0 - Displays languages in Language Manager table.
  - Part of `Translator Settings.language_manager`
  - Fields: `language_code`, `language_name`, `enabled`
  - Auto-populated from .po files and Language DocType
  - Synced to Language DocType on save

- **`Installed App` (Virtual DocType)**: A virtual resource that dynamically lists all apps installed on the current Frappe site.
  - Wraps `frappe.get_installed_apps()`
  - Used as the data source for the `App` DocType's `app_name` field to improve UX and prevent errors.

- **`Monitored App` (Child Table)**: Defines app/language combinations to monitor for automated translation.
  - Part of `Translator Settings.monitored_apps`
  - Links to `App` (source application) and `Language` (target language)
  - Used by scheduler to automatically create translation jobs when untranslated strings are detected

#### Workspace & UI Components

- **`Translation Hub` (Workspace)**: A dashboard for creating, managing, and monitoring Translation Jobs.
  - Displays **Dashboard Charts**:
    - **"Translations Over Time"**: Visualizes translation activity over time.
    - **"Monitored Apps Progress"**: Shows the percentage of translation completion for each monitored app/language.
  - Displays **Number Cards** for key metrics:
    - **Total Apps Tracked**: Count of apps configured for translation
    - **Jobs in Progress**: Active translation jobs currently running
    - **Jobs Completed (30 Days)**: Successfully completed jobs in the last 30 days
    - **Strings Translated**: Total number of strings translated across all jobs

#### Reports

- **`Monitored Apps Progress Report` (Script Report)**: Calculates the translation progress for monitored apps.
  - Used as the data source for the "Monitored Apps Progress" dashboard chart.
  - Logic located in `translation_hub/report/monitored_apps_progress_report/monitored_apps_progress_report.py`.

#### Background Jobs

- **Background Job (`tasks.py`)**: Functions enqueued by Frappe's scheduler or manually from the UI.
  - **`execute_translation_job(job_name)`**: Runs the translation process for a specific job
    - Updates job status (Queued → In Progress → Completed/Failed)
    - Instantiates and runs the `TranslationOrchestrator` with core logic components
    - Logs progress and errors to the job document
  - **`run_automated_translations()`**: Checks monitored apps and creates jobs automatically
    - Triggered by Frappe scheduler based on configured frequency
    - Scans for untranslated strings in monitored app/language combinations
    - Creates and enqueues new Translation Jobs when work is detected

### Core Logic Components (Classes)

```mermaid
classDiagram
    direction LR
    class FrappeUI {
        +TranslationJob
        +TranslatorSettings
        +App
        +MonitoredApp
        +TranslationHub
        +DashboardChart
        +NumberCards
        +InstalledApp
    }

    class BackgroundJob {
        +execute_translation_job(job_name)
        +ensure_pot_file(app_name)
    }

    class Orchestrator {
        -Config config
        -FileHandler file_handler
        -Service service
        -DocTypeLogger logger
        +run()
    }

    class Config {
        +str api_key
        +str model_name
        +int batch_size
        +int max_batch_retries
        +int max_single_retries
        +int retry_wait_seconds
        +str standardization_guide
        +Path pot_file
        +Path po_file
        +DocTypeLogger logger
        +bool use_database_storage
        +bool save_to_po_file
        +bool export_po_on_complete
        +from_json(config_path)
        +load_standardization_guide(guide_path)
    }

    class FileHandler {
        -Path po_path
        -DocTypeLogger logger
        +get_untranslated_entries()
        +update_entries()
        +save()
        +merge()
    }

    class Service {
        +translate(entries)*
    }

    class GeminiService {
        -Config config
        -DocTypeLogger logger
        +translate(entries)
    }

    class GroqService {
        -Config config
        -DocTypeLogger logger
        -OpenAI client
        +translate(entries)
    }

    class OpenRouterService {
        -Config config
        -DocTypeLogger logger
        -OpenAI client
        +translate(entries)
    }

    class MockTranslationService {
        -Config config
        -DocTypeLogger logger
        +translate(entries)
    }

    class DatabaseTranslationHandler {
        -str language
        -DocTypeLogger logger
        +save_translations(entries)
        +get_all_translations()
        +export_to_po(po_path)
    }

    class DocTypeLogger {
        -TranslationJob job_document
        +info(message)
        +warning(message)
        +error(message)
    }

    class GitSyncService {
        -TranslatorSettings settings
        -str repo_url
        -str branch
        -str token
        -Path repo_dir
        +setup_repo()
        +collect_translations()
        +distribute_translations()
        +backup()
        +restore()
    }

    class TranslationMaintenance {
        +fix_stuck_jobs()
        +fix_language_codes()
        +clear_caches()
        +verify_translations()
        +run_all()
    }

    class POImporter {
        +import_po_to_db(app, language)
        +import_all()
    }

    FrappeUI ..> BackgroundJob : enqueues
    BackgroundJob ..> Orchestrator : instantiates and runs
    BackgroundJob ..> Config : instantiates
    BackgroundJob ..> FileHandler : instantiates
    BackgroundJob ..> GeminiService : instantiates
    BackgroundJob ..> DocTypeLogger : instantiates
    BackgroundJob ..> GitSyncService : uses for backup/restore

    Orchestrator o-- Config
    Orchestrator o-- FileHandler
    Orchestrator o-- Service
    Orchestrator o-- DocTypeLogger
    Orchestrator ..> DatabaseTranslationHandler : uses

    GeminiService --|> Service
    GroqService --|> Service
    MockTranslationService --|> Service
    BackgroundJob ..> DatabaseTranslationHandler : instantiates
    BackgroundJob ..> GroqService : instantiates (if Groq provider)
    DocTypeLogger ..> FrappeUI : logs to TranslationJob
    GitSyncService ..> FrappeUI : reads TranslatorSettings
    POImporter ..> DatabaseTranslationHandler : uses
```

### DocType Relationships

The following diagram shows how the Frappe DocTypes relate to each other:

```mermaid
erDiagram
    TRANSLATOR_SETTINGS ||--o{ MONITORED_APP : "contains"
    TRANSLATOR_SETTINGS ||--o{ TRANSLATOR_LANGUAGE : "contains"
    MONITORED_APP }o--|| APP : "source_app"
    MONITORED_APP }o--|| LANGUAGE : "target_language"
    TRANSLATION_JOB }o--|| APP : "source_app"
    TRANSLATION_JOB }o--|| LANGUAGE : "target_language"
    APP_GLOSSARY }o--|| APP : "app"
    APP_GLOSSARY }o--|| LANGUAGE : "language"
    APP_GLOSSARY ||--o{ GLOSSARY_ITEM : "contains"
    
    TRANSLATOR_SETTINGS {
        string api_key
        bool enable_automated_translation
        string frequency
        bool use_database_storage
        bool save_to_po_file
        bool export_po_on_complete
        table monitored_apps
        table default_languages
    }
    
    MONITORED_APP {
        link source_app
        link target_language
    }
    
    TRANSLATOR_LANGUAGE {
        string language_code
        string language_name
        bool enabled
    }
    
    APP {
        link app_name "Link to Installed App"
        string app_title
        string domain
        string tone
        text description
        table do_not_translate
    }

    APP_GLOSSARY {
        link app
        link language
        table glossary_items
    }

    GLOSSARY_ITEM {
        string term
        string translation
        string description
    }

    INSTALLED_APP {
        string app_name "Virtual"
    }
    
    TRANSLATION_JOB {
        string title "Unique: Automated: {app} - {lang} - {timestamp}"
        string status
        link source_app
        link target_language
        int total_strings
        int translated_strings
        float progress_percentage
        datetime start_time
        datetime end_time
        text log
    }
    
    LANGUAGE {
        string language_code
        string language_name
    }
```

### Component Descriptions

- **`Orchestrator`**: The "brain" of the application. It coordinates the entire translation process. It is instantiated and run by the background job. Now supports both database and file-based storage.
- **`Service` (Abstract Base Class)**: Defines a common interface for any translation service.
- **`GeminiService`**: The concrete implementation of `Service` for the Google Gemini API. Handles **Context Injection** by fetching app-specific details (domain, tone, glossary) and embedding them into the LLM prompt.
- **`GroqService`**: An alternative implementation of `Service` that uses Groq's fast inference API. Uses the OpenAI-compatible SDK to call Groq endpoints. Supports models like `llama-3.3-70b-versatile` and `mixtral-8x7b-32768`. Selected via the `llm_provider` setting in Translator Settings.
- **`MockTranslationService`**: A test implementation of `Service` that simulates translation without API calls. Automatically used when API key starts with `"test-"`.
- **`DatabaseTranslationHandler`**: Stores translations in Frappe's Translation DocType (database). Provides highest priority for rendering and Docker-safe persistence.
- **`FileHandler`**: Encapsulates all logic related to file manipulation using the `polib` library. Handles merging `.pot` templates into `.po` files and saving translations.
- **`Config`**: A data class that holds all configuration parameters, including storage options (`use_database_storage`, `save_to_po_file`, `export_po_on_complete`).
- **`DocTypeLogger`**: A custom logger that writes output to the `log` field of a `Translation Job` document.
- **`GitSyncService`**: Manages Git-based backup and restore of translation files. Handles repository cloning, file synchronization, commits, and pushes to remote repositories.

### Translation Backup & Restore

The Translation Hub includes a Git-based backup system to persist translations across instances and facilitate disaster recovery.

#### GitSyncService

The `GitSyncService` class provides automated backup and restore functionality:

**Features:**
- **Repository Management**: Clones and syncs with remote Git repositories
- **File Collection**: Gathers `.po` files from all monitored apps
- **Directory Structure**: Organizes backups by version and app (`version/app_name/locale/*.po`)
- **Authentication**: Supports Personal Access Tokens (PAT) for private repositories
- **Automatic Commits**: Creates timestamped commits with `[skip ci]` tag
- **NEW in v1.6.0 - Selective Language Backup**: Only backs up/restores enabled languages
  - Filters by Language DocType `enabled` field
  - Significantly reduces repository size
  - Improves backup/restore performance
- **NEW in v1.6.1 - PO to Database Import**: Automatically imports restored .po files to Translation database
  - Parses .po files with `polib`
  - Populates `tabTranslation` for Translation Review functionality
  - Only imports enabled languages
- **NEW in v1.6.1 - Automatic Compilation**: Compiles .po to .mo files after restore
  - Uses `frappe.gettext.translate.compile_translations()`
  - Translations immediately available without manual `bench build`

**Configuration** (in Translator Settings):
- `backup_repo_url`: HTTPS URL of the Git repository
- `backup_branch`: Branch to use (default: `main`)
- `auth_token`: Personal Access Token for authentication
- `backup_frequency`: Automated backup schedule (None/Daily/Weekly)

**Storage Location**: `sites/[site_name]/private/translation_backup_repo`

**Repository Structure:**
```
translation-backup-repo/
├── version-16/  # Only major version for consistency
│   ├── frappe/
│   │   └── locale/
│   │       ├── pt_BR.po    # Only enabled languages
│   │       └── es.po
│   ├── erpnext/
│   │   └── locale/
│   │       └── pt_BR.po
│   └── custom_app/
│       └── locale/
│           └── pt_BR.po
```

**Usage:**
- **Manual Backup**: Click "Backup Translations" button in Translator Settings
  - Optional: Select specific apps to backup
- **Manual Restore**: Click "Restore Translations" button in Translator Settings
  - Optional: Select specific apps to restore
  - Automatically imports to database
  - Automatically compiles .mo files
- **Automated**: Configure `backup_frequency` for scheduled backups
- **Locale Cleanup**: NEW in v1.6.0 - Remove .po files of disabled languages
  - "Cleanup Locale Directories" button
  - Confirmation dialog for safety
  - Preserves _test.po files


### Database-First Approach & HTML Preservation

The Translation Hub uses a **database-first storage strategy** for translations, leveraging Frappe's built-in `Translation` DocType.

#### Why Database Storage?

1. **Docker-Safe**: Translations persist in the database, surviving container restarts
2. **Highest Priority**: Frappe loads translations in this order:
   - CSV files (legacy) - lowest priority
   - MO files (compiled .po) - medium priority
   - **Translation DocType** (database) - **highest priority** ✅
3. **Real-Time**: Changes apply immediately after cache clear
4. **Simple**: Uses Frappe's built-in infrastructure

#### HTML Preservation Strategy

> [!IMPORTANT]
> The `Translation` DocType automatically strips HTML tags from the `source_text` field for security. This can cause data loss if you rely solely on exporting from the database back to `.po` files.

To preserve rich text (HTML) in your translations:
1.  **Enable `save_to_po_file`**: This saves translations directly to the `.po` file in real-time, bypassing the database's HTML stripping.
2.  **Disable `export_po_on_complete`**: Prevent the database (which has stripped HTML) from overwriting the correct `.po` file at the end of the job.

#### Translation Loading Priority

```
User Opens App
    ↓
Frappe Loads Translations
    ↓
1. Load CSV Files (legacy)
    ↓
2. Load MO Files (.po compiled)
    ↓
3. Load Translation DocType (DATABASE) ← WINS!
    ↓
Merge All (database overrides files)
    ↓
Render in UI
```

**Result**: Database translations **always override** file-based translations!

### Configuration Options

The system supports three storage strategies via `TranslationConfig`:

#### Option 1: Database Only (Default - Recommended)

```python
use_database_storage = True   # Save to database
save_to_po_file = False        # Don't save .po files
export_po_on_complete = False  # Don't export
```

**Use Case**: Production deployment, Docker environments

**Benefits**:
- ✅ Simplest configuration
- ✅ Docker-safe persistence
- ✅ Real-time updates

#### Option 2: Database + .po Export

```python
use_database_storage = True   # Save to database
save_to_po_file = False        # Don't save during translation
export_po_on_complete = True   # Export at end
```

**Use Case**: Development, version control of translations (Plain text only)

**Benefits**:
- ✅ Database persistence
- ✅ .po files for Git commits
- ✅ External tool compatibility
- ⚠️ **Warning**: HTML tags will be stripped from source text in the exported file.

#### Option 3: Database + Real-time .po (Recommended for Rich Text)

```python
use_database_storage = True   # Save to database
save_to_po_file = True         # Also save .po files
export_po_on_complete = False  # Already saved
```

**Use Case**: Using external translation tools (Poedit, Weblate) or translating HTML content.

**Benefits**:
- ✅ Database persistence
- ✅ Real-time .po file updates
- ✅ Tool compatibility
- ✅ **Preserves HTML tags**

### File Paths (Frappe v16)

Translations use the `locale/` directory structure:

```
/apps/{app_name}/{app_name}/
├── locale/
│   ├── main.pot          # Template file (always "main.pot")
│   ├── es.po             # Spanish translations
│   ├── pt_BR.po          # Portuguese (Brazil)
│   └── ...
```

**Note**: Changed from `translations/` (old) to `locale/` (Frappe v16 standard)


## Execution Flow

The process can be triggered manually by a user or automatically by the Frappe scheduler.

```mermaid
sequenceDiagram
    participant User
    participant Workspace as Translation Workspace
    participant JobDoc as Translation Job DocType
    participant BGJob as Background Job (tasks.py)
    participant Orch as Orchestrator
    participant Service as Translation Service
    participant DBHandler as DatabaseTranslationHandler
    participant TransDoc as Translation DocType
    participant FileHandler as FileHandler (optional)

    alt Manual Trigger
        User->>Workspace: Clicks "Start Job"
        Workspace->>JobDoc: Calls `enqueue_job()`
    else Automated Trigger
        participant Scheduler
        Scheduler->>BGJob: Triggers `run_automated_translations()`
        BGJob->>JobDoc: Creates new Job & calls `enqueue_job()`
    end

    JobDoc->>BGJob: `frappe.enqueue(execute_translation_job)`
    
    BGJob->>JobDoc: Update status to 'In Progress'
    BGJob->>Orch: create(config, file_handler, service, logger)
    
    Note over BGJob,Service: Service selection based on API key
    alt API key starts with "test-"
        BGJob->>Service: Use MockTranslationService
    else Real API key
        BGJob->>Service: Use GeminiService
    end
    
    BGJob->>Orch: run()
    
    Orch->>FileHandler: merge() - merge .pot with .po
    Orch->>FileHandler: get_untranslated_entries()
    FileHandler-->>Orch: Return untranslated entries
    
    loop For each batch
        Orch->>Service: translate(batch)
        Service-->>Orch: Return translated batch
        
        Note over Orch,TransDoc: Database Storage (Primary)
        alt use_database_storage = True (default)
            Orch->>DBHandler: create(language, logger)
            Orch->>DBHandler: save_translations(batch)
            DBHandler->>TransDoc: Save/Update translations
            DBHandler->>DBHandler: clear_cache()
            Note over TransDoc: Translations now render in app!
        end
        
        Note over Orch,FileHandler: Optional .po File Storage
        alt save_to_po_file = True
            Orch->>FileHandler: update_entries(batch)
            Orch->>FileHandler: save()
        end
        
        Orch->>BGJob: (via logger) Update progress
        BGJob->>JobDoc: Save progress & log
    end
    
    Note over Orch,FileHandler: Optional .po Export
    alt export_po_on_complete = True
        Orch->>DBHandler: export_to_po(po_path)
        DBHandler->>TransDoc: get_all_translations()
        TransDoc-->>DBHandler: Return all translations
        DBHandler->>FileHandler: Write .po file
    end
    
    Orch-->>BGJob: Translation complete
    BGJob->>JobDoc: Update status to 'Completed'
    
    Note over User,TransDoc: Translations Render
    User->>Workspace: Opens app in target language
    Workspace->>TransDoc: Load translations (highest priority)
    TransDoc-->>Workspace: Return database translations
    Workspace->>User: Display translated UI
```

-   **Multi-Language**: A single application can be translated into multiple languages simultaneously. Each App/Language pair is treated as a distinct `Translation Job` and `Monitored App` entry.

## Context Generation Zoom-in

The quality of translation depends heavily on the context provided to the LLM. The system aggregates context from multiple sources to create a comprehensive `Standardization Guide`.

```mermaid
sequenceDiagram
    participant Job as Translation Job
    participant Task as execute_translation_job
    participant Settings as Translator Settings
    participant AppRow as Monitored App (Settings)
    participant LangRow as Translator Language (Settings)
    participant AppGlossary as App Glossary
    participant Config as TranslationConfig

    Job->>Task: Start Job (Source App, Target Lang)
    
    Note over Task: 1. Global Context
    Task->>Task: Load SYSTEM_PROMPT (Global Guide)
    
    Note over Task: 2. App-Specific Context
    Task->>Settings: Fetch Monitored App settings
    Settings-->>Task: Return App Settings
    opt If App Guide exists
        Task->>Task: Append App Standardization Guide
    end
    
    Note over Task: 3. Language-Specific Context
    Task->>Settings: Fetch Default Languages
    Settings-->>Task: Return Language Settings
    opt If Language Guide exists
        Task->>Task: Append Language Standardization Guide
    end
    
    Note over Task: 4. Glossary Context
    Task->>AppGlossary: Fetch Glossary for (App, Lang)
    AppGlossary-->>Task: Return Glossary Items
    loop For each term
        Task->>Task: Append "Term: Translation (Context)"
    end
    
    Note over Task: 5. Final Assembly
    Task->>Config: Create Config with combined Guide
    
    Note right of Config: The combined guide is now\nready to be sent to the LLM\nwith every translation request.
```


## AI Review Workflow

The v1.4.0 update introduces an AI-assisted review workflow, allowing the AI to act as a reviewer/suggester rather than just a translator.

```mermaid
sequenceDiagram
    participant User
    participant UI as Translation Finder UI
    participant ReviewAPI as translation_review.py
    participant Service as Translation Service
    participant ReviewDoc as Translation Review Doc

    Note over User, ReviewDoc: Scenario: Bulk Review with AI
    User->>UI: Search "Against" (Finds 100 items)
    User->>UI: Click "Review All" + Check "Use AI"
    UI->>ReviewAPI: create_bulk_reviews(search="Against", use_ai=True)
    
    ReviewAPI->>Service: batch_translate(source_texts)
    Service-->>ReviewAPI: Return [suggested_translations]
    
    loop For each item
        ReviewAPI->>ReviewDoc: Create(status="Pending", suggested_text=AI_Value)
    end
    
    ReviewAPI-->>UI: Created 100 reviews
    UI->>User: Show "Pending" reviews
    
    User->>ReviewDoc: Inspects & Approves
    ReviewDoc->>ReviewDoc: On Submit -> Update Translation DocType
```
