// Copyright (c) 2025, Sebastian Rodrigues and contributors
// For license information, please see license.txt

frappe.ui.form.on("Translation Review", {
	refresh(frm) {
		// Handle Copy Source click
		$(frm.wrapper).off("click", ".btn-copy-source").on("click", ".btn-copy-source", (e) => {
			e.preventDefault();
			if (frm.doc.status === "Pending") {
				frm.set_value("suggested_text", frm.doc.source_text);
			}
		});

		if (frm.doc.status === "Pending" && !frm.doc.__islocal) {
			// Allow editing the suggested text directly on the form
			frm.set_df_property("suggested_text", "read_only", 0);
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

			// Request AI Retranslation Button
			frm.add_custom_button(
				__("Request AI Retranslation"),
				() => {
					frappe.prompt(
						[
							{
								label: __("Instruction / Feedback for AI"),
								fieldname: "feedback",
								fieldtype: "Small Text",
								reqd: 1,
							},
						],
						(values) => {
							frappe.call({
								method: "translation_hub.translation_hub.doctype.translation_review.translation_review.request_ai_retranslation_inline",
								args: {
									review_name: frm.doc.name,
									feedback: values.feedback,
								},
								freeze: true,
								freeze_message: __("Asking AI for a new suggestion..."),
								callback: (r) => {
									if (r.message) {
										frm.reload_doc();
										frappe.show_alert({
											message: __("Suggested translation updated by AI"),
											indicator: "green",
										});
									}
								},
							});
						},
						__("Request AI Retranslation"),
						__("Request")
					);
				},
				"Actions"
			);

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
							frm.set_value("rejection_reason", values.reason);
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
		if (frm.doc.status === "Pending") {
			frm.dashboard.add_indicator(__("Pending Review"), "orange");
		} else if (frm.doc.status === "Approved") {
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

		// Check for rejection history
		check_rejection_history(frm);

		// Run counts and validation
		update_counts(frm);
		run_validation(frm);
	},
	suggested_text(frm) {
		update_counts(frm);
		run_validation(frm);
	}
});

function check_rejection_history(frm) {
	if (!frm.doc.source_text || !frm.doc.language) return;

	frappe.call({
		method: "translation_hub.translation_hub.doctype.translation_review.translation_review.check_rejection_history",
		args: {
			source_text: frm.doc.source_text,
			language: frm.doc.language,
		},
		callback: (r) => {
			if (r.message && r.message.rejection_count > 0) {
				const count = r.message.rejection_count;
				const last = frappe.datetime.str_to_user(r.message.last_rejection);
				const color = count >= 3 ? "red" : "orange";

				frm.dashboard.add_indicator(
					__("Rejected {0} times (Last: {1})", [count, last]),
					color
				);

				if (count >= 3) {
					frm.dashboard.set_headline_alert(
						__(
							"⚠️ Warning: This term has been rejected {0} times previously. Please verify carefully.",
							[count]
						),
						"red"
					);
				}
			}
		},
	});
}

function update_counts(frm) {
	const source_len = (frm.doc.source_text || "").length;
	const trans_len = (frm.doc.suggested_text || "").length;
	const source_words = (frm.doc.source_text || "").split(/\s+/).filter(Boolean).length;
	const trans_words = (frm.doc.suggested_text || "").split(/\s+/).filter(Boolean).length;

	const copy_link = frm.doc.status === "Pending"
		? `<a href="#" class="btn-copy-source" style="text-decoration: underline; font-weight: bold; cursor: pointer; float: right;">${__("Copy Source")}</a>`
		: "";

	const description = `${__("Characters")}: ${trans_len} (${__("Source")}: ${source_len}) | ${__("Words")}: ${trans_words} (${__("Source")}: ${source_words}) ${copy_link}`;

	frm.set_df_property("suggested_text", "description", description);
}

function run_validation(frm) {
	if (frm.doc.status !== "Pending") {
		frm.dashboard.clear_headline_alert();
		return;
	}
	if (!frm.doc.source_text || !frm.doc.suggested_text) return;

	frappe.call({
		method: "translation_hub.translation_hub.doctype.translation_review.translation_review.validate_translation_text",
		args: {
			source_text: frm.doc.source_text,
			target_text: frm.doc.suggested_text
		},
		callback: (r) => {
			if (r.message) {
				const warnings = r.message.warnings || [];
				if (warnings.length > 0) {
					let alertHtml = `<div style="text-align: left;">`;
					alertHtml += `<strong>⚠️ ${__("Translation Quality Warnings:")}</strong>`;
					alertHtml += `<ul style="margin-top: 5px; margin-bottom: 0; padding-left: 20px;">`;
					warnings.forEach(w => {
						alertHtml += `<li>${__(w)}</li>`;
					});
					alertHtml += `</ul></div>`;
					frm.dashboard.set_headline_alert(alertHtml, "orange");
				} else {
					frm.dashboard.clear_headline_alert();
				}
			}
		}
	});
}
