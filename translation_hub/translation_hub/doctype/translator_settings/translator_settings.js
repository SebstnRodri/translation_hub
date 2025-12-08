// Copyright (c) 2025, Sebastian Rodrigues and contributors
// For license information, please see license.txt

frappe.ui.form.on("Translator Settings", {
	refresh(frm) {
		if (!frm.doc.backup_repo_url) return;

		frm.add_custom_button(
			__("Backup Translations"),
			function () {
				frappe.confirm(
					__("Are you sure you want to backup translations to the remote repository?"),
					function () {
						frappe.call({
							method: "translation_hub.tasks.backup_translations",
							freeze: true,
							freeze_message: __("Backing up translations..."),
							callback: function (r) {
								if (!r.exc) {
									frappe.msgprint(__("Backup initiated successfully."));
								}
							},
						});
					}
				);
			},
			__("Backup / Restore")
		);

		frm.add_custom_button(
			__("Restore Translations"),
			function () {
				frappe.confirm(
					__(
						"Are you sure you want to restore translations from the remote repository? This will overwrite local files."
					),
					function () {
						frappe.call({
							method: "translation_hub.tasks.restore_translations",
							freeze: true,
							freeze_message: __("Restoring translations..."),
							callback: function (r) {
								if (!r.exc) {
									frappe.msgprint(__("Restore initiated successfully."));
								}
							},
						});
					}
				);
			},
			__("Backup / Restore")
		);
	},

	test_connection(frm) {
		frappe.call({
			method: "translation_hub.translation_hub.doctype.translator_settings.translator_settings.test_api_connection",
			freeze: true,
			freeze_message: __("Testing API connection..."),
			callback: function (r) {
				if (r.message) {
					if (r.message.success) {
						frappe.msgprint({
							title: __("Connection Test"),
							indicator: "green",
							message: r.message.message,
						});
					} else {
						frappe.msgprint({
							title: __("Connection Test"),
							indicator: "red",
							message: r.message.message,
						});
					}
				}
			},
		});
	},
});
