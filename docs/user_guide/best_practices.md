# Best Practices for High-Quality Translations

This guide provides tips and best practices for achieving the best possible translation quality with the AI model.

## Preserving HTML & Rich Text

If your application uses HTML tags in translatable strings (e.g., `Welcome <b>User</b>`), you must configure the storage settings correctly to prevent data loss.

**Recommended Settings:**
- **Use Database Storage**: ✅ Checked
- **Save to .po File**: ✅ Checked (Real-time saving preserves HTML)
- **Export .po File on Completion**: ❌ Unchecked (Database export strips HTML)

> [!WARNING]
> The database automatically strips HTML tags for security. If you enable "Export .po File on Completion", it will overwrite your correct files with stripped text. Always rely on "Save to .po File" for rich text content.
