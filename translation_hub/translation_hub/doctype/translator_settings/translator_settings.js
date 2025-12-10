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

		const fetch_apps_and_show_dialog = (title, primary_action_label, action_method) => {
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Installed App",
					fields: ["app_name"],
					limit_page_length: 50,
				},
				freeze: true,
				freeze_message: __("Fetching installed apps..."),
				callback: function (r) {
					let installed_apps = [];
					if (r.message) {
						installed_apps = r.message.map((d) => d.app_name);
					}

					frappe.prompt(
						[
							{
								label: __("Select Apps (Leave empty for all)"),
								fieldname: "apps",
								fieldtype: "MultiSelect",
								options: installed_apps,
								description: __(
									"Only selected apps will be processed. All apps if empty."
								),
							},
						],
						function (values) {
							let apps = values.apps
								? values.apps
										.split(",")
										.map((s) => s.trim())
										.filter((s) => s)
								: [];

							let perform_action = () => {
								frappe.call({
									method: "translation_hub.tasks." + action_method,
									args: {
										apps: apps.length > 0 ? apps : null,
									},
									freeze: true,
									freeze_message: __("Processing..."),
									callback: function (r) {
										if (!r.exc) {
											frappe.msgprint(
												__("Operation completed successfully.")
											);
										}
									},
								});
							};

							if (action_method === "restore_translations") {
								frappe.confirm(
									__(
										"Are you sure you want to restore? This will overwrite local files for the selected apps."
									),
									perform_action
								);
							} else {
								perform_action();
							}
						},
						title,
						primary_action_label
					);
				},
			});
		};

		frm.add_custom_button(
			__("Backup Translations"),
			function () {
				fetch_apps_and_show_dialog(
					__("Backup Configuration"),
					__("Start Backup"),
					"backup_translations"
				);
			},
			__("Backup / Restore")
		);

		frm.add_custom_button(
			__("Restore Translations"),
			function () {
				fetch_apps_and_show_dialog(
					__("Restore Configuration"),
					__("Select"),
					"restore_translations"
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
