// Copyright (c) 2025, Sebastian Rodrigues and contributors
// For license information, please see license.txt

frappe.ui.form.on("Translator Settings", {
	refresh(frm) {
		// Add Refresh Models button
		frm.add_custom_button(
			__("Refresh Models"),
			function () {
				frm.trigger("fetch_models");
			},
			__("LLM")
		);

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

	llm_provider(frm) {
		// Clear current model selection when provider changes
		if (frm.doc.llm_provider === "Gemini") {
			// Keep existing value or clear
		} else if (frm.doc.llm_provider === "Groq") {
			frm.set_value("groq_model", "");
		} else if (frm.doc.llm_provider === "OpenRouter") {
			frm.set_value("openrouter_model", "");
		}
	},

	fetch_models(frm) {
		const provider = frm.doc.llm_provider || "Gemini";

		frappe.call({
			method: "translation_hub.translation_hub.doctype.translator_settings.translator_settings.fetch_available_models",
			args: { provider: provider },
			freeze: true,
			freeze_message: __("Fetching available models..."),
			callback: function (r) {
				if (r.message && r.message.length > 0) {
					// Show model selection dialog
					let models = r.message;
					let options = models.map((m) => m.label);

					frappe.prompt(
						[
							{
								fieldname: "model",
								label: __("Select Model"),
								fieldtype: "Autocomplete",
								options: options,
								reqd: 1,
							},
						],
						function (values) {
							// Find the selected model's value
							let selected = models.find((m) => m.label === values.model);
							if (selected) {
								if (provider === "Gemini") {
									frm.set_value("api_key", frm.doc.api_key); // Keep as is
									frappe.msgprint(
										__(
											"Selected model: {0}. Note: Gemini model is set in code.",
											[selected.value]
										)
									);
								} else if (provider === "Groq") {
									frm.set_value("groq_model", selected.value);
									frm.save();
								} else if (provider === "OpenRouter") {
									frm.set_value("openrouter_model", selected.value);
									frm.save();
								}
							}
						},
						__("Select {0} Model", [provider]),
						__("Select")
					);
				} else {
					frappe.msgprint({
						title: __("No Models Found"),
						indicator: "orange",
						message: __(
							"No models were returned. Please check that your API key is configured correctly."
						),
					});
				}
			},
		});
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
