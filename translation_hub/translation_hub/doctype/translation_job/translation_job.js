// Copyright (c) 2025, Sebastian Rodrigues and contributors
// For license information, please see license.txt

frappe.ui.form.on("Translation Job", {
	refresh: function (frm) {
		if (
			frm.doc.status === "Pending" ||
			frm.doc.status === "Failed" ||
			frm.doc.status === "Cancelled"
		) {
			frm.add_custom_button(__("Start Job"), function () {
				frm.call("enqueue_job").then((r) => {
					frm.reload_doc();
					frappe.show_alert({
						message: __("Job enqueued successfully"),
						indicator: "green",
					});
				});
			}).addClass("btn-primary");
		}
	},

	before_save: function (frm) {
		// Only check for new documents or when changing app/language
		if (!frm.doc.source_app || !frm.doc.target_language) {
			return;
		}

		// Skip if already confirmed or if job is not pending
		if (frm.doc.__confirmed_existing || frm.doc.status !== "Pending") {
			return;
		}

		// Check for existing translations
		return new Promise((resolve, reject) => {
			frappe.call({
				method: "translation_hub.translation_hub.doctype.translation_job.translation_job.check_existing_translations",
				args: {
					source_app: frm.doc.source_app,
					target_language: frm.doc.target_language,
				},
				async: false,
				callback: function (r) {
					if (r.message && r.message.has_existing) {
						frappe.confirm(
							r.message.message,
							() => {
								// User confirmed - proceed with save
								frm.doc.__confirmed_existing = true;
								resolve();
							},
							() => {
								// User cancelled
								frappe.validated = false;
								reject();
							}
						);
					} else {
						resolve();
					}
				},
			});
		});
	},

	source_app: function (frm) {
		// Reset confirmation when app changes
		frm.doc.__confirmed_existing = false;
	},

	target_language: function (frm) {
		// Reset confirmation when language changes
		frm.doc.__confirmed_existing = false;
	},
});
