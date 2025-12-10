console.log("Translation Review List Script Loaded - Fixed");

frappe.listview_settings["Translation Review"] = {
	onload: function (listview) {
		listview.page.add_inner_button(__("Fix Translation"), function () {
			new TranslationFinderDialog(listview);
		});
	},
};

class TranslationFinderDialog {
	constructor(listview) {
		this.listview = listview;
		this.dialog = new frappe.ui.Dialog({
			title: __("Find and Fix Translation"),
			fields: [
				{
					fieldname: "language",
					label: __("Idioma"),
					fieldtype: "Link",
					options: "Language",
					default: "pt-BR",
					reqd: 1,
				},
				{
					fieldname: "search_term",
					label: __("Search Text (Source or Translated)"),
					fieldtype: "Data",
					description: __("Type at least 3 characters"),
					onchange: () => this.search_translations(),
				},
				{
					fieldname: "results_html",
					fieldtype: "HTML",
				},
			],
			primary_action_label: __("Fechar"),
			primary_action: () => this.dialog.hide(),
		});

		this.dialog.show();
	}

	search_translations() {
		let values = this.dialog.get_values();
		if (!values.search_term || values.search_term.length < 3) return;

		// Default to 'erpnext' since we removed the selector
		// This assumes the user is primarily fixing ERPNext or that 'erpnext' is a safe default container
		const source_app = "erpnext";

		frappe.call({
			method: "translation_hub.translation_hub.doctype.translation_review.translation_review.get_translations_for_review",
			args: {
				source_app: source_app,
				language: values.language,
				search_text: values.search_term,
				limit: 10,
			},
			debounce: 500,
			callback: (r) => {
				this.render_results(r.message || [], source_app);
			},
		});
	}

	render_results(translations, source_app) {
		let html = `<div class="list-group" style="margin-top: 15px;">`;

		if (translations.length === 0) {
			html += `<div class="list-group-item">${__("No translations found.")}</div>`;
		} else {
			// Add 'Review All' button if there are many results
			if (translations.length > 1) {
				html += `
                    <div class="list-group-item list-group-item-warning d-flex justify-content-between align-items-center">
                        <span>${__("Found {0} results.", [translations.length])}</span>
                        <button class="btn btn-sm btn-primary" onclick="cur_dialog.create_bulk_reviews()">
                            ${__("Review All ({0})", [translations.length])}
                        </button>
                    </div>
                `;
			}

			translations.forEach((t) => {
				const source = frappe.utils.escape_html(t.source_text);
				const trans = frappe.utils.escape_html(
					t.translated_text || __("(No translation)")
				);
				// We need to pass source_app to create_review too
				html += `
                    <div class="list-group-item list-group-item-action flex-column align-items-start"
                         style="cursor: pointer;"
                         onclick="cur_dialog.create_review('${source}');">
                        <div class="d-flex w-100 justify-content-between">
                            <h5 class="mb-1">${source}</h5>
                        </div>
                        <p class="mb-1 text-muted">${trans}</p>
                        <small class="text-primary">${__("Click to fix this one")}</small>
                    </div>
                `;
			});
		}

		html += `</div>`;
		this.dialog.fields_dict.results_html.$wrapper.html(html);

		// Attach helpers to dialog instance
		// We use closure to keep access to source_app
		this.dialog.create_review = (text) => this.create_review(text, source_app);
		this.dialog.create_bulk_reviews = () => this.create_bulk_reviews(source_app);
	}

	create_review(source_text, source_app) {
		let values = this.dialog.get_values();

		frappe.call({
			method: "translation_hub.translation_hub.doctype.translation_review.translation_review.create_translation_review",
			args: {
				source_text: source_text,
				language: values.language,
				source_app: source_app,
			},
			freeze: true,
			callback: (res) => {
				if (res.message) {
					this.dialog.hide();
					frappe.set_route("Form", "Translation Review", res.message);
				}
			},
		});
	}

	create_bulk_reviews(source_app) {
		let values = this.dialog.get_values();

		const dialog = new frappe.ui.Dialog({
			title: __("Bulk Review Options"),
			fields: [
				{
					fieldname: "info_html",
					fieldtype: "HTML",
					options: `<div class="text-muted small">${__(
						"This will create {0} review records.",
						[this.last_results_count || "multiple"]
					)}</div>`,
				},
				{
					fieldname: "use_ai",
					label: __("Use AI to Suggest Corrections"),
					fieldtype: "Check",
					default: 0,
					description: __(
						"If checked, AI will generate suggested translations instead of using current values."
					),
				},
				{
					fieldname: "ai_context",
					label: __("Context for AI (Optional)"),
					fieldtype: "Small Text",
					depends_on: "eval:doc.use_ai == 1",
					description: __(
						"E.g., 'Financial context, use formal tone' or 'Glossary: Against -> Vínculo'"
					),
				},
			],
			primary_action_label: __("Create Reviews"),
			primary_action: () => {
				const opts = dialog.get_values();
				dialog.hide();

				frappe.call({
					method: "translation_hub.translation_hub.doctype.translation_review.translation_review.create_bulk_reviews",
					args: {
						search_text: values.search_term,
						language: values.language,
						source_app: source_app,
						use_ai: opts.use_ai,
						ai_context: opts.ai_context,
					},
					freeze: true,
					freeze_message: opts.use_ai
						? __("Asking AI for suggestions...")
						: __("Creating reviews..."),
					callback: (res) => {
						this.dialog.hide();
						frappe.msgprint(__("Reviews created: {0}", [res.message]));
						if (this.listview) this.listview.refresh();
					},
				});
			},
		});

		dialog.show();
	}
}
