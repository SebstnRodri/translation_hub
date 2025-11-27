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
2. Enter your **Google Gemini API Key**.
3. **Language Setup**:
    - Scroll to the "Language Setup" section.
    - Add the languages you want to use (e.g., `pt-BR`, `es-MX`) in the "Default Languages" table.
    - Check "Enabled" for each language.
    - **Save** the settings. The languages will be created/enabled automatically! 
    *(Alternatively, you can run `bench setup-languages` in the terminal after configuring this).*
4. **Storage Settings**:
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

## 4. Automated Translation (Optional)

Instead of manually creating jobs, you can let the Translation Hub handle it for you:

1. Open **Translator Settings**.
2. Check **Enable Automated Translation**.
3. Set the **Frequency** (e.g., `Daily` or `Weekly`).
4. In the **Monitored Apps** table, add the apps and languages you want to keep updated (e.g., `frappe` -> `pt-BR`).
5. **Save**.

The system will now periodically check these apps for new untranslated strings and automatically create jobs for them!
