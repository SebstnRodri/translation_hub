# Architecture Guide

This document describes the overall architecture and design principles of the `translation_hub` application.

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
  - Fields: `api_key`, `standardization_guide`, `enable_automated_translation`, `frequency`, `monitored_apps`

- **`Translation Job` (Standard DocType)**: Represents a single translation task, tracking its status, progress, timing, and logs.
  - Links to `App` (source application) and `Language` (target language)
  - Tracks progress metrics: `total_strings`, `translated_strings`, `progress_percentage`
  - Records timing: `start_time`, `end_time`
  - Maintains execution log for debugging and monitoring
  - Status values: Pending, Queued, In Progress, Completed, Failed, Cancelled

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

**Configuration** (in Translator Settings):
- `backup_repo_url`: HTTPS URL of the Git repository
- `backup_branch`: Branch to use (default: `main`)
- `auth_token`: Personal Access Token for authentication
- `backup_frequency`: Automated backup schedule (None/Daily/Weekly)

**Storage Location**: `sites/[site_name]/private/translation_backup_repo`

**Repository Structure:**
```
translation-backup-repo/
├── develop/ (or version-15/)
│   ├── frappe/
│   │   └── locale/
│   │       ├── pt_BR.po
│   │       ├── es.po
│   │       └── fr.po
│   ├── erpnext/
│   │   └── locale/
│   │       └── pt_BR.po
│   └── custom_app/
│       └── locale/
│           └── pt_BR.po
```

**Usage:**
- **Manual Backup**: Click "Backup Translations" button in Translator Settings
- **Manual Restore**: Click "Restore Translations" button in Translator Settings
- **Automated**: Configure `backup_frequency` for scheduled backups


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

