# Getting Started 🚀

This guide will walk you through the steps to set up the Translation Hub and run your first translation.

## 1. Installation (CLI)

Install the app on your Frappe bench via terminal:

```bash
bench get-app https://github.com/SebstnRodri/translation_hub
bench install-app translation_hub
```

## 2. Configuration (UI)

1. Open **Translator Settings** in your Frappe Desk.
2. **Select LLM Provider**:
    - **Gemini** (default): Uses Google Gemini API
    - **Groq**: Uses Groq's fast inference API (Llama, Mixtral models)
3. Enter your API Key for the selected provider:
    - For Gemini: Enter **Gemini API Key**
    - For Groq: Enter **Groq API Key** and optionally change the model (default: `llama-3.3-70b-versatile`)
4. **Language Setup**:
    - Scroll to the "Language Setup" section.
    - Add the languages you want to use (e.g., `pt-BR`, `es-MX`) in the "Default Languages" table.
    - Check "Enabled" for each language.
    - **Save** the settings. The languages will be created/enabled automatically! 
    *(Alternatively, you can run `bench setup-languages` in the terminal after configuring this).*
5. **Storage Settings**:
    - **Use Database Storage**: ✅ Checked (Recommended for Docker/Production)
    - **Save to .po File**: ✅ Checked (Recommended for preserving HTML/Rich Text)
    - **Export .po File on Completion**: ❌ Unchecked (Avoids overwriting files with stripped data)

## 3. Usage via Desk (UI)

The entire translation process is managed through the Frappe Desk interface. You **do not** need to manually generate POT files; the system handles this automatically.

1. Search for **Translation Job** in the awesome bar.
2. Click **Add Translation Job**.
3. Select the **Source App** (e.g., `frappe`, `erpnext`) and **Target Language** (e.g., `pt-BR`, `es`).
4. Save the document.
5. Click the **Start Job** button in the top right corner.
6. Watch the agent work! The status will update as strings are translated.

## 4. Managing Glossaries

To ensure consistent terminology for specific apps and languages (e.g., translating "File" as "Arquivo" in Portuguese for a specific app), use the **App Glossary**.

1. Open the **App** you want to configure (e.g., `translation_hub`).
2. Click on the **App Glossary** link in the dashboard.
3. Click **Add App Glossary**.
4. Select the **Language** (e.g., `pt-BR`).
5. In the **Glossary Items** table, add your terms:
    - **Term**: The original English term (e.g., "File").
    - **Translation**: The desired translation (e.g., "Arquivo").
    - **Description**: Optional context (e.g., "Menu item").
6. **Save**.

These terms will now be automatically included in the context for any translation job matching this App and Language.

## 5. Automated Translation (Optional)

Instead of manually creating jobs, you can let the Translation Hub handle it for you:

1. Open **Translator Settings**.
2. Check **Enable Automated Translation**.
3. Set the **Frequency** (e.g., `Daily` or `Weekly`).
4. In the **Monitored Apps** table, add the apps and languages you want to keep updated (e.g., `frappe` -> `pt-BR`).
5. **Save**.

The system will now periodically check these apps for new untranslated strings and automatically create jobs for them!

## 6. Backup & Restore Translations

To persist translations across instances or create backups, configure Git-based backup:

### Setup Backup Repository

1. Create a Git repository (GitHub, GitLab, Bitbucket, etc.)
2. Generate a **Personal Access Token** (PAT) with write permissions
3. Open **Translator Settings**
4. Scroll to **Backup Configuration** section
5. Configure:
   - **Backup Repository URL**: `https://github.com/your-user/translations-backup.git`
   - **Backup Branch**: `main` (or your preferred branch)
   - **Auth Token (PAT)**: Paste your Personal Access Token
   - **Backup Frequency**: Choose `None`, `Daily`, or `Weekly`
6. **Save**

### Manual Backup

Click the **Backup Translations** button in Translator Settings. This will:
- Collect all `.po` files from monitored apps
- Organize them by app (`app_name/locale/*.po`)
- Commit and push to your repository

### Manual Restore

Click the **Restore Translations** button in Translator Settings. This will:
- Pull latest changes from the repository
- Distribute `.po` files back to their respective apps
- Preserve translations across new instances

### Automated Backup

Set **Backup Frequency** to `Daily` or `Weekly` for automatic backups.

> **Note**: Backups are stored in `sites/[site_name]/private/translation_backup_repo`
