// Copyright (c) 2025, Sebastian Rodrigues and contributors
// For license information, please see license.txt

frappe.ui.form.on("Translation Task", {
    refresh(frm) {
        // Style the source and translation fields for better comparison
        if (frm.doc.source_text) {
            frm.set_df_property("source_text", "description", "Original text to be translated");
        }

        // Pre-populate corrected_translation with suggested if empty
        if (!frm.doc.corrected_translation && frm.doc.suggested_translation) {
            frm.set_value("corrected_translation", frm.doc.suggested_translation);
        }
    },

    save_translation_btn(frm) {
        // Validate before calling
        if (!frm.doc.corrected_translation && !frm.doc.suggested_translation) {
            frappe.msgprint({
                title: __("Missing Translation"),
                indicator: "red",
                message: __(
                    "Please enter a corrected translation or ensure there is an AI suggested translation."
                ),
            });
            return;
        }

        frappe.confirm(
            __(
                "This will save the translation to the database and mark this task as completed. Continue?"
            ),
            () => {
                frappe.call({
                    method: "translation_hub.translation_hub.doctype.translation_task.translation_task.save_translation",
                    args: {
                        task_name: frm.doc.name,
                    },
                    freeze: true,
                    freeze_message: __("Saving translation..."),
                    callback: (r) => {
                        if (r.message && r.message.success) {
                            frappe.show_alert(
                                {
                                    message: __(r.message.message),
                                    indicator: "green",
                                },
                                5
                            );
                            frm.reload_doc();
                        }
                    },
                });
            }
        );
    },

    retranslate_btn(frm) {
        frappe.confirm(
            __(
                "This will ask the AI to generate a new translation considering the rejection reason. Continue?"
            ),
            () => {
                frappe.call({
                    method: "translation_hub.translation_hub.doctype.translation_task.translation_task.request_retranslation",
                    args: {
                        task_name: frm.doc.name,
                    },
                    freeze: true,
                    freeze_message: __("Requesting AI retranslation..."),
                    callback: (r) => {
                        if (r.message) {
                            if (r.message.success) {
                                frappe.show_alert(
                                    {
                                        message: __(r.message.message),
                                        indicator: "green",
                                    },
                                    5
                                );
                                frm.reload_doc();
                            } else {
                                frappe.msgprint({
                                    title: __("Retranslation Failed"),
                                    indicator: "red",
                                    message: r.message.message,
                                });
                            }
                        }
                    },
                });
            }
        );
    },
});
