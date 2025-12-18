// Copyright (c) 2025, Sebastian Rodrigues and contributors
// For license information, please see license.txt

frappe.ui.form.on("Translation Review", {
	refresh(frm) {
		// Add prominent button to go to Review Center
		if (frm.doc.status === "Pending" && !frm.doc.__islocal) {
			// Make form read-only for pending items - edit should be done in Review Center
			frm.set_df_property("suggested_text", "read_only", 1);
			frm.set_df_property("status", "read_only", 1);

			// Approve Button
			frm.add_custom_button(
				__("Approve"),
				() => {
					frm.set_value("status", "Approved");
					frm.save().then(() => {
						frappe.show_alert({
							message: __("Translation Approved"),
							indicator: "green",
						});
					});
				},
				"Actions"
			).addClass("btn-success");

			// Reject Button
			frm.add_custom_button(
				__("Reject"),
				() => {
					frappe.prompt(
						[
							{
								label: __("Rejection Reason"),
								fieldname: "reason",
								fieldtype: "Small Text",
								reqd: 1,
							},
						],
						(values) => {
							frm.set_value("status", "Rejected");
							frm.set_value("rejection_reason", values.reason); // Assume field exists or will be added
							frm.save().then(() => {
								frappe.show_alert({
									message: __("Translation Rejected"),
									indicator: "red",
								});
							});
						},
						__("Reject Translation"),
						__("Reject")
					);
				},
				"Actions"
			).addClass("btn-danger");
		}

		// Show status indicator
		if (frm.doc.status === "Approved") {
			frm.dashboard.add_indicator(__("Approved"), "green");
		} else if (frm.doc.status === "Rejected") {
			frm.dashboard.add_indicator(__("Rejected"), "red");

			// Add button to retry with AI using rejection feedback
			frm.add_custom_button(
				__("Retry with AI"),
				() => {
					frappe.call({
						method: "translation_hub.translation_hub.doctype.translation_review.translation_review.retry_translation_with_feedback",
						args: {
							review_name: frm.doc.name,
						},
						freeze: true,
						freeze_message: __(
							"Asking AI for a new translation with feedback context..."
						),
						callback: (r) => {
							if (r.message) {
								frappe.msgprint({
									title: __("New Review Created"),
									indicator: "green",
									message: __(
										"A new Translation Review has been created with AI suggestion based on your feedback: {0}",
										[
											`<a href="/desk/Form/Translation Review/${r.message}">${r.message}</a>`,
										]
									),
								});
							}
						},
					});
				},
				__("Actions")
			);
		}
	},
});
