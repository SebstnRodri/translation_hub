# Getting Started 🚀

This guide will walk you through the steps to set up the Translation Hub and run your first translation.

## 1. Installation (CLI)

Install the app on your Frappe bench via terminal:

```bash
bench get-app https://github.com/SebstnRodri/translation_hub
bench install-app translation_hub
```

**Tip**: Run the setup command to enable common languages (like `pt-BR`, `es-MX`):

```bash
bench setup-languages
```

## 2. Configuration (UI)

1. Open **Translator Settings** in your Frappe Desk.
2. Enter your **Google Gemini API Key**.
3. Ensure **Use Database Storage** is checked (recommended).

## 3. Usage via Desk (UI)

The entire translation process is managed through the Frappe Desk interface:

1. Search for **Translation Job** in the awesome bar.
2. Click **Add Translation Job**.
3. Select the **Source App** (e.g., `frappe`, `erpnext`) and **Target Language** (e.g., `pt-BR`, `es`).
4. Save the document.
5. Click the **Start Job** button in the top right corner.
6. Watch the agent work! The status will update as strings are translated.
