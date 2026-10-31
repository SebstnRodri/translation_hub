# Copyright (c) 2026, Sebastian Rodrigues and contributors
# For license information, please see license.txt

from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from translation_hub.api.locale_compiler_api import publish_ecosystem_translations
from translation_hub.core.locale_compiler import (
	SUPPORTED_APPS,
	LocaleCompiler,
	invalidate_translation_cache,
)


class TestLocaleCompiler(FrappeTestCase):
	"""
	Suíte de testes para o serviço LocaleCompiler e endpoints de publicação
	de traduções globais .mo.
	"""

	def setUp(self):
		self.compiler = LocaleCompiler()
		self.original_user = frappe.session.user
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user(self.original_user)

	def test_supported_apps_contains_ecosystem_apps(self):
		"""Verifica se os apps canônicos do ecossistema estão presentes na lista suportada."""
		expected = ["frappe", "erpnext", "smart_pos", "frappe_br_toolkit"]
		for app in expected:
			self.assertIn(app, SUPPORTED_APPS)

	def test_compile_ecosystem_execution(self):
		"""Verifica a compilação determinística para smart_pos e erpnext."""
		report = self.compiler.compile_ecosystem(
			apps=["smart_pos", "erpnext"],
			locale="pt_BR",
			force=True,
		)

		self.assertEqual(report.total_errors, 0, f"Erros durante compilação: {report.errors}")
		self.assertEqual(report.total_compiled, 2)

		compiled_apps = [c.app for c in report.compiled]
		self.assertIn("smart_pos", compiled_apps)
		self.assertIn("erpnext", compiled_apps)

		for item in report.compiled:
			mo_file = Path(item.mo_path)
			self.assertTrue(mo_file.exists(), f"Arquivo .mo não existe: {mo_file}")
			self.assertGreater(mo_file.stat().st_size, 0)

	def test_compile_ecosystem_skips_nonexistent_po(self):
		"""Garante que apps sem catálogo PO sejam pulados graciosamente sem lançar exceção."""
		report = self.compiler.compile_ecosystem(
			apps=["cardflow", "financas"],
			locale="pt_BR",
			force=True,
		)
		self.assertEqual(report.total_errors, 0)
		self.assertEqual(report.total_compiled, 0)
		self.assertEqual(report.total_skipped, 2)

	def test_invalidate_translation_cache(self):
		"""Verifica se a invalidação centralizada de cache executa com sucesso."""
		cleared = invalidate_translation_cache()
		self.assertIsInstance(cleared, list)

	def test_whitelisted_api_admin_permission(self):
		"""Verifica que usuários sem privilégios de Admin/System Manager são bloqueados."""
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			publish_ecosystem_translations()

	def test_whitelisted_api_success(self):
		"""Verifica o endpoint Whitelisted com retorno estruturado via Pydantic."""
		frappe.set_user("Administrator")
		result = publish_ecosystem_translations(
			apps=["smart_pos"],
			locale="pt_BR",
			force=True,
			invalidate_cache=False,
		)

		self.assertTrue(result.get("success"))
		self.assertGreaterEqual(result.get("total_compiled", 0), 1)
		self.assertIn("smart_pos", [c["app"] for c in result["report"]["compiled"]])
