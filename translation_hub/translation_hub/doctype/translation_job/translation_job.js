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
});
