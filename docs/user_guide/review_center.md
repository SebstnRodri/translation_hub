# Review Center 📝

The Review Center is a dedicated interface for reviewing and refining AI-generated translations. It provides a streamlined workflow for approving, rejecting, and teaching the AI to improve future translations.

## 1. Accessing the Review Center

You can access the Review Center in several ways:

- **Search**: Type "Review Center" in the Awesome Bar
- **URL**: Navigate directly to `/desk/review-center`
- **From Translation Review list**: Click the link in the info banner
- **From Translation Review form**: Click the "Review Center" link in the blue banner (this will open directly to that specific review)

## 2. Interface Overview

The Review Center uses a split-panel layout:

### Left Panel: Review List

- Shows all **Pending** translations that need review
- Each item displays:
  - Source text preview (truncated)
  - Source app badge
- Click any item to select it for review
- Counter shows total pending reviews

### Right Panel: Detail View

When a review is selected, you can see:

- **Source Text**: The original English text
- **Current Translation**: The existing translation (if any)
- **Suggested Translation**: AI-generated suggestion (editable!)
- **Action Buttons**: Approve ✓ and Reject ✕

### Filters

At the top of the page:

- **App**: Filter by source application (frappe, erpnext, etc.)
- **Language**: Filter by target language (default: pt-BR)

## 3. Reviewing Translations

### Approving a Translation

1. Select a review from the left panel
2. Review the suggested translation
3. Optionally edit the text in the "Suggested Translation" field
4. Click **Approve** (or press `A` key)

The translation will be:
- Saved to the Translation DocType
- Exported to the `.po` file
- Synced to the backup repository (if configured)

### Rejecting a Translation

1. Select a review from the left panel
2. Click **Reject** (or press `R` key)
3. In the dialog, fill in:
   - **Rejection Reason** (required): Explain why the translation is incorrect
   - **Problematic Term** (optional): The specific word/phrase that was mistranslated
   - **Correct Translation** (optional): How that term should be translated

4. Click **Confirmar** to submit

> [!TIP]
> **Term Correction** is a powerful feature! When you specify a problematic term and its correct translation, the AI will learn this rule and apply it to all future translations.

## 4. Keyboard Shortcuts

For efficient reviewing, use these keyboard shortcuts:

| Key | Action |
|-----|--------|
| `A` | Approve current review |
| `R` | Reject current review |
| `↓` | Select next review |
| `↑` | Select previous review |

## 5. AI Feedback Loop

The Translation Hub includes an intelligent feedback system that helps the AI learn from your corrections.

### How It Works

1. **Rejection with Context**: When you reject a translation and provide a reason, this feedback is stored
2. **Term Corrections**: Specific term rules (e.g., "against" → "vinculado a") are given high priority
3. **Few-Shot Learning**: Full translation corrections are used as examples for the AI

### Term Correction Priority

Term corrections appear in the AI prompt as **CRITICAL TERM RULES**:

```
**CRITICAL TERM RULES (Always follow these):**
- 'against' → translate as 'vinculado a' (not 'contra')
- 'file' → translate as 'arquivo' (not 'ficheiro')
```

These rules take precedence over general translation patterns.

### Retry with AI

If a translation was rejected, you can request a new AI suggestion that incorporates your feedback:

1. Open the rejected Translation Review form
2. Click **Actions → Retry with AI**
3. A new review will be created with an improved suggestion

The AI receives:
- The original rejection reason
- All learned term corrections
- Previous examples of corrections

## 6. Deep Links

You can link directly to a specific review:

```
/desk/review-center?review=TR-000123
```

This is useful for:
- Sharing a specific translation for discussion
- Navigating from the Translation Review form
- Creating bookmarks for pending reviews

## 7. Integration with Translation Review List

The Translation Review list view includes:

- **Status indicators**: Color-coded badges (Pending = orange, Approved = green, Rejected = red)
- **Fix Translation button**: Opens a search dialog to find and create new reviews
- **Info banner**: Link to the Review Center

### Fix Translation Dialog

The "Fix Translation" feature allows you to:

1. Search for translations by text
2. See matching source and translated texts
3. Click individual items to create a single review
4. Use "Review All" to create reviews for all matches
5. Optionally enable AI suggestions during bulk creation

## 8. Best Practices

1. **Be specific with rejections**: Detailed feedback helps the AI learn faster
2. **Use term corrections**: For consistently mistranslated terms, always fill in the problematic term and correct translation
3. **Review in batches**: Use keyboard shortcuts to quickly process many translations
4. **Check AI suggestions**: Even approved translations may need minor edits
5. **Use the Retry feature**: For rejected items, let the AI try again with your feedback before manually writing the translation
