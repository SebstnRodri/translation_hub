// Copyright (c) 2025, Sebastian Rodrigues and contributors
// For license information, please see license.txt

frappe.ui.form.on("Translation Review", {
	refresh(frm) {
		// Add prominent button to go to Review Center
		if (frm.doc.status === "Pending" && !frm.doc.__islocal) {
			// Make form read-only for pending items - edit should be done in Review Center
			frm.set_df_property('suggested_text', 'read_only', 1);
			frm.set_df_property('status', 'read_only', 1);

			// Add info message with link to this specific review
			frm.dashboard.add_comment(
				__('Use <a href="/desk/review-center?review={0}">Review Center</a> to edit this translation.', [frm.doc.name]),
				'blue',
				true
			);

			// Primary action: Go to Review Center
			frm.page.set_primary_action(__("Open Review Center"), () => {
				frappe.set_route('review-center');
			}, 'review');
		}

		// Show status indicator
		if (frm.doc.status === "Approved") {
			frm.dashboard.add_indicator(__("Approved"), "green");
		} else if (frm.doc.status === "Rejected") {
			frm.dashboard.add_indicator(__("Rejected"), "red");

			// Add button to retry with AI using rejection feedback
			frm.add_custom_button(__("Retry with AI"), () => {
				frappe.call({
					method: "translation_hub.translation_hub.doctype.translation_review.translation_review.retry_translation_with_feedback",
					args: {
						review_name: frm.doc.name
					},
					freeze: true,
					freeze_message: __("Asking AI for a new translation with feedback context..."),
					callback: (r) => {
						if (r.message) {
							frappe.msgprint({
								title: __("New Review Created"),
								indicator: "green",
								message: __("A new Translation Review has been created with AI suggestion based on your feedback: {0}",
									[`<a href="/desk/Form/Translation Review/${r.message}">${r.message}</a>`])
							});
						}
					}
				});
			}, __("Actions"));
		}
	},
});
