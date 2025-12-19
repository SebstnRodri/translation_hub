frappe.ui.form.on("Translator Settings", {
	refresh(frm) {
		// Automatically fetch models if API key is present
		frm.trigger("fetch_models_silent");

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

		// Specific button for Standard Repository workflow
		frm.add_custom_button(
			__("Download Standard Translations"),
			function () {
				fetch_apps_and_show_dialog(
					__("Download Standard Translations"),
					__("Download & Sync"),
					"restore_translations"
				);
			},
			__("Backup / Restore")
		);

		// Cleanup locale directories button
		frm.add_custom_button(
			__("Cleanup Locale Directories"),
			function () {
				frappe.confirm(
					__(
						"This will permanently delete .po files of disabled languages from monitored apps. Make sure to backup first!<br><br>Continue?"
					),
					function () {
						fetch_apps_and_show_dialog(
							__("Cleanup Locale Directories"),
							__("Cleanup"),
							"cleanup_locale_directories"
						);
					}
				);
			},
			__("Language Manager")
		);
	},

	llm_provider(frm) {
		// Clear current model selection when provider changes
		if (frm.doc.llm_provider === "Gemini") {
			frm.set_value("gemini_model", "");
		} else if (frm.doc.llm_provider === "Groq") {
			frm.set_value("groq_model", "");
		} else if (frm.doc.llm_provider === "OpenRouter") {
			frm.set_value("openrouter_model", "");
		}
	},

	// Trigger on save if keys changed
	after_save(frm) {
		frm.trigger("fetch_models_silent");
	},

	fetch_models_silent(frm) {
		const provider = frm.doc.llm_provider;
		let api_key_field = "";
		let model_field = "";

		if (provider === "Groq") {
			api_key_field = "groq_api_key";
			model_field = "groq_model";
		} else if (provider === "OpenRouter") {
			api_key_field = "openrouter_api_key";
			model_field = "openrouter_model";
		} else if (provider === "Gemini") {
			api_key_field = "api_key";
			model_field = "gemini_model";
		} else {
			return;
		}

		if (!frm.doc[api_key_field]) {
			// No key, clear options
			set_model_options(frm, model_field, []);
			return;
		}

		frappe.call({
			method: "translation_hub.translation_hub.doctype.translator_settings.translator_settings.fetch_available_models",
			args: { provider: provider },
			callback: function (r) {
				if (r.message && r.message.length > 0) {
					let options = r.message.map((m) => m.value);
					set_model_options(frm, model_field, options);
				} else {
					set_model_options(frm, model_field, ["Check API Key"]);
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
						// Also refresh models on successful connection
						frm.trigger("fetch_models_silent");
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

	sync_languages_button(frm) {
		frappe.call({
			method: "translation_hub.translation_hub.doctype.translator_settings.translator_settings.populate_language_manager_table",
			freeze: true,
			freeze_message: __("Loading all languages..."),
			callback: function (r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			},
		});
	},

	save_language_settings(frm) {
		frappe.call({
			method: "translation_hub.translation_hub.doctype.translator_settings.translator_settings.save_language_manager_settings",
			freeze: true,
			freeze_message: __("Saving language settings..."),
			callback: function (r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			},
		});
	},
});

function set_model_options(frm, fieldname, options) {
	if (options.length > 0) {
		frm.set_df_property(fieldname, "options", options.join("\n"));
		// If current value is not in options, set to first
		if (!options.includes(frm.doc[fieldname])) {
			frm.set_value(fieldname, options[0]);
		}
	} else {
		frm.set_df_property(fieldname, "options", "");
	}
	frm.refresh_field(fieldname);
}
