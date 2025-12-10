console.log("Translation Review List Script Loaded");
frappe.listview_settings["Translation Review"] = {
	onload: function (listview) {
		listview.page.add_inner_button(__("Fix Translation"), function () {
			new TranslationFinderDialog();
		});
	},
};

class TranslationFinderDialog {
	constructor() {
		this.dialog = new frappe.ui.Dialog({
			title: __("Find and Fix Translation"),
			fields: [
				{
					fieldname: "source_app",
					label: __("Target App"),
					fieldtype: "Link",
					options: "Installed App",
					default: "erpnext",
					description: __("The app this translation belongs to (Search is global)"),
					reqd: 1,
				},
				{
					fieldname: "language",
					label: __("Language"),
					fieldtype: "Link",
					options: "Language",
					default: "pt-BR", // Default to pt-BR as user seems to be using it
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
					label: __("Results"),
					fieldtype: "HTML",
				},
			],
			primary_action_label: __("Close"),
			primary_action: () => {
				this.dialog.hide();
			},
		});

		this.dialog.show();
	}

	search_translations() {
		let values = this.dialog.get_values();
		if (!values.search_term || values.search_term.length < 3) return;

		frappe.call({
			method: "translation_hub.translation_hub.doctype.translation_review.translation_review.get_translations_for_review",
			args: {
				source_app: values.source_app,
				language: values.language,
				search_text: values.search_term,
				limit: 10,
			},
			callback: (r) => {
				this.render_results(r.message || []);
			},
		});
	}

	render_results(translations) {
		let html = `<div class="list-group">`;

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
				// Escape HTML to prevent injection
				const source = frappe.utils.escape_html(t.source_text);
				const trans = frappe.utils.escape_html(
					t.translated_text || __("(No translation)")
				);

				html += `
                    <a href="#" class="list-group-item list-group-item-action flex-column align-items-start" onclick="cur_dialog.create_review('${source}'); return false;">
                        <div class="d-flex w-100 justify-content-between">
                            <h5 class="mb-1">${source}</h5>
                        </div>
                        <p class="mb-1 text-muted">${trans}</p>
                        <small class="text-primary">${__("Click to fix this one")}</small>
                    </a>
                `;
			});
		}

		html += `</div>`;
		this.dialog.fields_dict.results_html.$wrapper.html(html);

		// Attach helpers
		this.dialog.create_review = (source_text) => this.create_review(source_text);
		this.dialog.create_bulk_reviews = () => this.create_bulk_reviews();
	}

	create_bulk_reviews() {
		let values = this.dialog.get_values();
		if (!values.search_term) return;

		frappe.confirm(__("This will create {0} review records. Continue?", [__("all")]), () => {
			frappe.call({
				method: "translation_hub.translation_hub.doctype.translation_review.translation_review.create_bulk_reviews",
				args: {
					source_app: values.source_app,
					language: values.language,
					search_text: values.search_term,
				},
				freeze: true,
				callback: (r) => {
					if (r.message) {
						this.dialog.hide();
						frappe.msgprint(
							__("{0} reviews created! Go to list view to edit.", [r.message])
						);
						frappe.set_route("List", "Translation Review");
					}
				},
			});
		});
	}

	create_review(source_text) {
		let values = this.dialog.get_values();

		frappe.call({
			method: "translation_hub.translation_hub.doctype.translation_review.translation_review.create_translation_review",
			args: {
				source_text: source_text, // Passed raw
				// Actually the onclick passes it as string literal.
				language: values.language,
				source_app: values.source_app,
			},
			freeze: true,
			filters: {}, // Not needed
			callback: (r) => {
				if (r.message) {
					this.dialog.hide();
					frappe.set_route("Form", "Translation Review", r.message);
				}
			},
			error: (r) => {
				// If error is duplicate, we should probably just navigate to existing?
				// The API throws error, so this callback handles generic failure.
			},
		});
	}
}
