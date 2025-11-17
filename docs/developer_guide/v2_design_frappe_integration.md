# v2.0.0 Design: Frappe Integration

This document outlines the design for version 2.0.0 of the Translation Hub, focusing on its integration as a full-fledged Frappe application. The goal is to provide a seamless, UI-driven experience for managing and executing translation jobs directly from the Frappe Desk.

## 1. Overview

The primary objective of v2.0.0 is to transform the existing command-line translation tool into a fully integrated Frappe application. This will enable system administrators and users to:
- Configure translation settings (API keys, standardization guides) via the UI.
- Create, manage, and monitor translation jobs for different apps and languages.
- View real-time progress and logs of translation processes.
- Eliminate the need for command-line access for translation tasks.

## 2. Components (Frappe DocTypes & Pages)

The application will introduce new Frappe components to achieve its goals:

### a. `Translator Settings` (DocType)

*   **Purpose**: A Singleton DocType to store global configuration settings for the translator.
*   **Type**: Singleton (only one record exists in the system).
*   **Fields**:
    *   `api_key` (Data / Password): Securely stores the API key.
    *   `standardization_guide` (Text Editor / Markdown Editor): Allows users to define and edit the standardization rules or glossary directly within the UI.
    *   A "Automation" section break.
    *   `enable_automated_translation` (Check): A checkbox to enable or disable the automated translation scheduler.
    *   `frequency` (Select): Defines how often the automated job runs. Options: `Daily`, `Weekly`.
    *   `monitored_apps` (Table): A child table where users can specify which app/language combinations to monitor automatically. Columns: `source_app` (Link to App), `target_language` (Link to Language).

### b. `Translation Job` (DocType)

*   **Purpose**: Represents a single translation task for a specific Frappe app and language. Each document of this DocType will track the lifecycle of a translation.
*   **Type**: Standard DocType.
*   **Fields**:
    *   `title` (Data): Auto-generated title (e.g., "App Name - Language Translation").
    *   `source_app` (Link to App): The Frappe application to be translated (e.g., "erpnext", "frappe").
    *   `target_language` (Link to Language): The target language for the translation (e.g., "pt-BR").
    *   `status` (Select): Current status of the job (`Pending`, `In Progress`, `Completed`, `Failed`, `Cancelled`).
    *   `total_strings` (Int): Total number of translatable strings identified.
    *   `translated_strings` (Int): Number of strings successfully translated.
    *   `progress_percentage` (Float / Read-only): Calculated field showing `(translated_strings / total_strings) * 100`.
    *   `start_time` (Datetime): When the job started.
    *   `end_time` (Datetime): When the job finished.
    *   `log` (Text Editor / Small Text): Stores the detailed output log of the translation process. This will be updated incrementally.

### c. `Translation Workspace` (Desk Page)

*   **Purpose**: The main user interface for managing and monitoring translation activities. This will serve as a dashboard.
*   **Layout**: Structured with dashboard components (Cards, List Views, Quick Actions).

#### i. Metrics Section (Top Dashboard Cards)

A set of `Dashboard Chart` cards (type "Number") providing an at-a-glance overview:
*   **Total Apps Tracked**: Count of distinct Frappe apps for which translation jobs exist.
*   **Jobs in Progress**: Count of `Translation Job` documents with `status: 'In Progress'`.
*   **Jobs Completed (Last 30 Days)**: Count of successful jobs completed within the last month.
*   **Strings Translated (All Time)**: Sum of `translated_strings` across all completed `Translation Job` documents.

#### ii. Recent Translation Jobs (Main List View)

A dynamic list or table displaying recent `Translation Job` documents, with key information:
*   **Columns**: `title`, `source_app`, `target_language`, `status` (with color coding), `progress_percentage` (or `translated_strings / total_strings`), `modified` (last updated time).
*   Each row will link directly to the full `Translation Job` document for detailed viewing.

#### iii. Quick Actions & Integrated Links (Sidebar or Header)

Provides easy access to common tasks and related Frappe resources:
*   **Primary Action**: A prominent "Create New Translation Job" button (opens a dialog to create a new `Translation Job` document).
*   **Links**:
    *   "Translator Settings": Link to the `Translator Settings` singleton DocType.
    *   "View All Jobs": Link to the standard list view of the `Translation Job` DocType.
    *   "Frappe Languages": Link to Frappe's standard `Language` DocType list view.
    *   "Official Translations Portal": External link to the Frappe community forum for translations (e.g., `discuss.frappe.io/c/translations`).

## 3. Automation Module

To minimize manual work and keep translations up-to-date, an automation module will be included. This module will periodically check for new strings in monitored apps and automatically create translation jobs.

### a. Implementation via Frappe Scheduler

*   The automation will be driven by Frappe's built-in scheduler. A new scheduled event will be added to the app's `hooks.py` file.
    ```python
    # in hooks.py
    scheduler_events = {
        "daily": [
            "translation_hub.tasks.run_automated_translations"
        ]
    }
    ```
*   This configuration will execute the `run_automated_translations` function once every day.

### b. Automation Logic (`tasks.py`)

A new file, `tasks.py`, will contain the core logic for the scheduled job.

1.  **Check if Enabled**: The function will first check the `enable_automated_translation` flag in `Translator Settings`. If disabled, it will terminate.
2.  **Iterate Monitored Apps**: It will fetch the `monitored_apps` table from `Translator Settings` and loop through each user-defined `app`/`language` pair.
3.  **Intelligent Job Creation**: For each pair, the task will:
    *   Perform a "dry run" merge of the `.pot` and `.po` files to see if there are any new or fuzzy strings.
    *   Check if an active (`Pending` or `In Progress`) `Translation Job` for that same pair already exists.
    *   **If** there are new strings to translate **and** no active job exists, it will automatically create a new `Translation Job` document and enqueue it for processing.
    *   If there is nothing to do, it moves to the next pair, ensuring no unnecessary jobs are created.

This "set it and forget it" approach turns the tool into a continuous localization system.

## 4. Flow

### a. User Flow

1.  **Configuration**: An admin navigates to `Translator Settings`, saves their API key, and optionally defines a standardization guide.
2.  **Automation Setup (Optional)**: The admin enables `Automated Translation`, sets a `Frequency`, and adds one or more `app`/`language` pairs to the `Monitored Apps` table.
3.  **Manual Job (Optional)**: The admin can still manually create a one-off job from the `Translation Workspace`.
4.  **Monitoring**: The admin can check the `Translation Workspace` at any time to see the status of both automatically and manually created jobs.

### b. System Flow (Backend Logic)

1.  **Manual Trigger**: A user clicks "Start Translation" on a `Translation Job` document, which enqueues a background job.
2.  **Automated Trigger**: The Frappe Scheduler runs the `run_automated_translations` task daily. This task identifies work to be done and enqueues one or more background jobs.
3.  **Job Execution**: The background job (whether triggered manually or automatically) will:
    *   Update the `Translation Job` document's `status` to `In Progress`.
    *   Dynamically determine the paths for the `.pot` and `.po` files.
    *   Retrieve settings from `Translator Settings`.
    *   Instantiate and execute the core logic (`TranslationOrchestrator`).
    *   Capture logs and progress, updating the `Translation Job` document.
    *   Set the final status (`Completed` or `Failed`) upon completion.

## 5. Integrations

*   **Frappe Framework**: Extensive use of Frappe's core features:
    *   DocTypes for data modeling (`Translator Settings`, `Translation Job`).
    *   Desk Pages for UI (`Translation Workspace`).
    *   **Scheduler** for automated, recurring tasks.
    *   `frappe.enqueue` for asynchronous background processing.
    *   `frappe.whitelist` for exposing Python methods to the client-side.
    *   `frappe.get_app_path` for dynamic file path resolution.
*   **Core Translator Logic**: The existing `translation_hub.core` module will be directly imported and utilized by the Frappe backend logic.

## 6. Implementation Details

*   **Logging**: The `Orchestrator` will need a mechanism to redirect its output to the `Translation Job`'s log field. This could be achieved by passing a callable logger function to the orchestrator.
*   **Progress Updates**: The `Translation Job` document will be saved periodically (e.g., after each batch) to update the `log` and progress fields.
*   **Security**: API keys will be stored securely using Frappe's built-in password field encryption.

## 7. Extensibility

The modular design of the core translation logic ensures that:
*   New translation providers can be added by implementing new `TranslationService` subclasses.
*   The system can be extended to support other translation file formats if needed, by extending `TranslationFile`.

This design provides a clear roadmap for developing v2.0.0 as a robust and user-friendly Frappe application.
