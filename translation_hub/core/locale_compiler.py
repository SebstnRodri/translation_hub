# Copyright (c) 2026, Sebastian Rodrigues and contributors
# For license information, please see license.txt

import logging
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import frappe
from frappe import _
from frappe.gettext.translate import (
	compile_translations,
	get_locale_dir,
	get_mo_path,
	get_po_path,
)
from frappe.translate import MERGED_TRANSLATION_KEY, USER_TRANSLATION_KEY, clear_cache
from frappe.utils import get_bench_path, get_sites

logger = logging.getLogger("translation_hub.locale_compiler")

SUPPORTED_APPS: list[str] = [
	"frappe",
	"erpnext",
	"smart_pos",
	"frappe_br_toolkit",
	"translation_hub",
]


@dataclass
class CompiledAppResult:
	app: str
	locale: str
	mo_path: str
	size_bytes: int


@dataclass
class SkippedAppResult:
	app: str
	locale: str
	reason: str


@dataclass
class FailedAppResult:
	app: str
	locale: str
	error: str


@dataclass
class CompilationReport:
	locale: str
	compiled: list[CompiledAppResult] = field(default_factory=list)
	skipped: list[SkippedAppResult] = field(default_factory=list)
	errors: list[FailedAppResult] = field(default_factory=list)

	@property
	def total_compiled(self) -> int:
		return len(self.compiled)

	@property
	def total_skipped(self) -> int:
		return len(self.skipped)

	@property
	def total_errors(self) -> int:
		return len(self.errors)

	def to_dict(self) -> dict[str, Any]:
		return {
			"locale": self.locale,
			"total_compiled": self.total_compiled,
			"total_skipped": self.total_skipped,
			"total_errors": self.total_errors,
			"compiled": [asdict(item) for item in self.compiled],
			"skipped": [asdict(item) for item in self.skipped],
			"errors": [asdict(item) for item in self.errors],
		}


class LocaleCompiler:
	"""
	Serviço centralizado para compilação e distribuição de catálogos de tradução .MO
	(GNU Gettext / Babel) a partir do SaaS Manager para todo o ecossistema multi-tenant.
	Conforme ADR 0034 e Translation Distribution Plan.
	"""

	def __init__(self, supported_apps: list[str] | None = None):
		self.supported_apps = supported_apps or SUPPORTED_APPS

	def compile_ecosystem(
		self,
		apps: list[str] | None = None,
		locale: str = "pt_BR",
		force: bool = True,
	) -> CompilationReport:
		"""
		Itera sobre os apps suportados (ou lista fornecida) e compila catálogos .po em binários .mo
		diretamente no caminho canônico de assets: sites/assets/locale/{locale}/LC_MESSAGES/{app}.mo
		"""
		target_apps = apps or self.supported_apps
		available_apps = set(frappe.get_all_apps(True))
		report = CompilationReport(locale=locale)

		logger.info(f"Iniciando compilação de traduções para locale '{locale}' em {len(target_apps)} apps.")

		for app in target_apps:
			if app not in available_apps:
				logger.warning(f"App '{app}' não encontrado no bench. Pulando.")
				report.skipped.append(
					SkippedAppResult(app=app, locale=locale, reason="App não instalado no bench")
				)
				continue

			po_path: Path = get_po_path(app, locale)
			if not po_path.exists():
				logger.info(f"App '{app}' não possui catálogo PO em {po_path}. Pulando.")
				report.skipped.append(
					SkippedAppResult(
						app=app,
						locale=locale,
						reason=f"Arquivo de catálogo não encontrado: {po_path.name}",
					)
				)
				continue

			try:
				logger.info(f"Compilando traduções para '{app}' ({locale})...")
				compile_translations(target_app=app, locale=locale, force=force)

				mo_path: Path = get_mo_path(app, locale)
				if mo_path.exists():
					# Sincronização defensiva caso sites/assets e bench/assets sejam diretórios físicos distintos
					self._sync_to_bench_assets(app, locale, mo_path)

					size = mo_path.stat().st_size
					logger.info(f"✓ Binário .MO gerado com sucesso: {mo_path} ({size} bytes)")
					report.compiled.append(
						CompiledAppResult(
							app=app,
							locale=locale,
							mo_path=str(mo_path),
							size_bytes=size,
						)
					)
				else:
					err_msg = f"Compilação executada mas binário .mo não foi encontrado em {mo_path}"
					logger.error(err_msg)
					report.errors.append(FailedAppResult(app=app, locale=locale, error=err_msg))

			except Exception as e:
				logger.exception(f"Erro ao compilar traduções para app '{app}': {e}")
				report.errors.append(FailedAppResult(app=app, locale=locale, error=str(e)))

		logger.info(
			f"Compilação concluída: {report.total_compiled} compilados, "
			f"{report.total_skipped} pulados, {report.total_errors} erros."
		)
		return report

	def _sync_to_bench_assets(self, app: str, locale: str, mo_path: Path) -> None:
		"""
		Garante que o arquivo .mo também esteja presente em /assets/locale caso não seja symlink.
		"""
		try:
			bench_path = Path(get_bench_path())
			direct_assets_locale = bench_path / "assets" / "locale" / locale / "LC_MESSAGES"
			target_file = direct_assets_locale / f"{app}.mo"

			# Se o caminho de sites/assets for diferente fisicamente do caminho assets
			if direct_assets_locale.resolve() != mo_path.parent.resolve():
				direct_assets_locale.mkdir(parents=True, exist_ok=True)
				shutil.copy2(mo_path, target_file)
				logger.debug(f"Sincronizado .mo para pasta física de assets: {target_file}")
		except Exception as e:
			logger.warning(f"Aviso na sincronização de assets física para '{app}': {e}")

	@staticmethod
	def invalidate_cache(site_name: str | None = None) -> list[str]:
		"""
		Invalida o cache Redis de traduções (merged_translations e bootinfo)
		para o site especificado ou para todos os sites do bench.
		Opera exclusivamente sobre a camada de cache Redis, sem exigir conexão com o MariaDB.
		"""
		cleared_sites: list[str] = []
		target_sites = [site_name] if site_name else get_sites()
		original_site = getattr(frappe.local, "site", None)

		for site in target_sites:
			try:
				frappe.init(site=site)
				if frappe.cache:
					frappe.cache.delete_key("merged_translations")
					frappe.cache.delete_key(MERGED_TRANSLATION_KEY)
					frappe.cache.delete_key(USER_TRANSLATION_KEY)
					frappe.cache.delete_key("bootinfo")
					cleared_sites.append(site)
					logger.info(f"Cache de tradução limpo com sucesso para o site: {site}")
			except Exception as e:
				logger.warning(f"Não foi possível invalidar cache para o site '{site}': {e}")
			finally:
				try:
					frappe.destroy()
				except Exception:
					pass

		# Restaura o contexto do site original se necessário
		if original_site:
			try:
				frappe.init(site=original_site)
			except Exception:
				pass

		return cleared_sites


def invalidate_translation_cache(site_name: str | None = None) -> list[str]:
	"""Helper global para invalidação de cache de traduções."""
	return LocaleCompiler.invalidate_cache(site_name=site_name)
