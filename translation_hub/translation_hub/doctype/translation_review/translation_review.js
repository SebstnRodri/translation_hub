// Copyright (c) 2025, Sebastian Rodrigues and contributors
// For license information, please see license.txt

frappe.ui.form.on("Translation Review", {
	refresh(frm) {
		if (frm.doc.status === "Pending" && !frm.doc.__islocal) {
			frm.add_custom_button(
				__("Ask AI Suggestion"),
				() => {
					const context_prompt = "Generate a better translation";

					frappe.prompt(
						[
							{
								fieldname: "ai_context",
								label: __("Context for AI (Optional)"),
								fieldtype: "Small Text",
								description: __('E.g. "Formal tone", "Financial term"'),
							},
						],
						(values) => {
							frappe.call({
								method: "translation_hub.translation_hub.doctype.translation_review.translation_review.get_ai_suggestion",
								args: {
									source_text: frm.doc.source_text,
									language: frm.doc.language,
									source_app: frm.doc.source_app,
									context: values.ai_context,
								},
								freeze: true,
								freeze_message: __("Asking AI..."),
								callback: (r) => {
									if (r.message) {
										frm.set_value("suggested_text", r.message);
										frappe.msgprint(__("Suggestion applied!"));
									}
								},
							});
						},
						__("AI Translation Helper"),
						__("Generate")
					);
				},
				"Actions"
			);
		}
	},
});
