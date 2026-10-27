# Copyright (c) 2026, Sebastian Rodrigues and contributors
# For license information, please see license.txt

import json
from typing import Any

import frappe
from frappe import _
from pydantic import BaseModel, Field, ValidationError

from translation_hub.core.locale_compiler import LocaleCompiler, invalidate_translation_cache


class PublishTranslationsRequest(BaseModel):
	apps: list[str] | None = Field(
		default=None,
		description="Lista de apps a compilar. Se omitido, compila todos os apps suportados.",
	)
	locale: str = Field(
		default="pt_BR",
		description="Locale alvo para compilação Gettext (padrão: pt_BR)",
	)
	force: bool = Field(
		default=True,
		description="Forçar recompilação mesmo se o arquivo .mo já existir",
	)
	invalidate_cache: bool = Field(
		default=True,
		description="Invalidar cache Redis de traduções após compilação",
	)


@frappe.whitelist()
def publish_ecosystem_translations(
	apps: Any | None = None,
	locale: str = "pt_BR",
	force: Any = True,
	invalidate_cache: Any = True,
) -> dict[str, Any]:
	"""
	Endpoint Whitelisted seguro para compilação e publicação de traduções .mo nos assets globais.
	Acesso restrito a System Manager / Administrator do SaaS Manager.
	"""
	if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
		frappe.throw(
			_("Apenas Administradores do SaaS podem publicar traduções globais nos assets."),
			frappe.PermissionError,
		)

	# Normalização de tipos vindos de requisições web ou form_dict
	parsed_apps: list[str] | None = None
	if apps is not None:
		if isinstance(apps, str):
			try:
				parsed = json.loads(apps)
				parsed_apps = parsed if isinstance(parsed, list) else [str(parsed)]
			except Exception:
				parsed_apps = [a.strip() for a in apps.split(",") if a.strip()]
		elif isinstance(apps, list):
			parsed_apps = [str(a) for a in apps]

	parsed_force = force
	if isinstance(force, str):
		parsed_force = force.lower() in ("true", "1", "yes")

	parsed_invalidate = invalidate_cache
	if isinstance(invalidate_cache, str):
		parsed_invalidate = invalidate_cache.lower() in ("true", "1", "yes")

	try:
		req = PublishTranslationsRequest(
			apps=parsed_apps,
			locale=locale,
			force=bool(parsed_force),
			invalidate_cache=bool(parsed_invalidate),
		)
	except ValidationError as e:
		frappe.throw(_("Parâmetros inválidos: {0}").format(e), frappe.ValidationError)

	compiler = LocaleCompiler()
	report = compiler.compile_ecosystem(apps=req.apps, locale=req.locale, force=req.force)

	cleared_sites = []
	if req.invalidate_cache:
		cleared_sites = compiler.invalidate_cache()

	return {
		"success": report.total_errors == 0,
		"report": report.to_dict(),
		"total_compiled": report.total_compiled,
		"total_skipped": report.total_skipped,
		"total_errors": report.total_errors,
		"cleared_sites": cleared_sites,
		"message": _("{0} apps compilados com sucesso para o idioma '{1}' nos assets globais.").format(
			report.total_compiled, req.locale
		),
	}


@frappe.whitelist()
def clear_ecosystem_translation_cache(site_name: str | None = None) -> dict[str, Any]:
	"""
	Endpoint seguro para invalidar o cache de traduções em Redis.
	"""
	if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
		frappe.throw(
			_("Apenas Administradores do SaaS podem invalidar o cache de traduções."),
			frappe.PermissionError,
		)

	cleared = invalidate_translation_cache(site_name=site_name)
	return {
		"success": True,
		"cleared_sites": cleared,
		"message": _("Cache de traduções limpo com sucesso para {0} site(s).").format(len(cleared)),
	}
