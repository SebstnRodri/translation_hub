// Translation Hub Workspace & Global Action Integration (ADR 0034)
frappe.router.on("change", () => {
	const route = frappe.get_route();
	if (route && route[0] === "translation-hub" && !route[1]) {
		setup_translation_hub_workspace_actions();
	}
});

$(document).on("page-change", () => {
	const route = frappe.get_route();
	if (route && route[0] === "translation-hub" && !route[1]) {
		setup_translation_hub_workspace_actions();
	}
});

function setup_translation_hub_workspace_actions() {
	if (!frappe.user_roles || (!frappe.user_roles.includes("System Manager") && frappe.session.user !== "Administrator")) {
		return;
	}

	setTimeout(() => {
		const cur_page = frappe.pages["translation-hub"] || frappe.container?.page;
		if (!cur_page || !cur_page.page) return;

		// Evita duplicação do botão
		if (cur_page.page.wrapper.find(".btn-publish-translations").length > 0) {
			return;
		}

		const btn = cur_page.page.add_inner_button(__("Publicar Traduções nos Assets"), function () {
			frappe.confirm(
				__(
					"Deseja compilar e publicar os arquivos binários (.mo) de tradução nos assets para todos os inquilinos SaaS?"
				),
				function () {
					frappe.call({
						method: "translation_hub.api.locale_compiler_api.publish_ecosystem_translations",
						args: {
							locale: "pt_BR",
							force: true,
							invalidate_cache: true,
						},
						freeze: true,
						freeze_message: __("Compilando e publicando traduções globais (.mo)..."),
						callback: function (r) {
							if (!r.exc && r.message) {
								frappe.msgprint({
									title: __("Traduções Publicadas"),
									indicator: "green",
									message: __(
										"Traduções compiladas com sucesso!<br>Total de apps compilados: <b>{0}</b>",
										[r.message.total_compiled]
									),
								});
							}
						},
					});
				}
			);
		});

		btn.addClass("btn-publish-translations btn-primary");
	}, 300);
}
