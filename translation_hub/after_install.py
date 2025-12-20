# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

"""
Post-installation setup script for Translation Hub.

This script runs after the app is installed and sets up:
- Default Translator Settings (Agent Pipeline enabled)
- Regional Expert Profile for ERPNext pt-BR with Brazilian fiscal rules
"""

import frappe


def after_install():
	"""Setup default configurations after app installation."""
	try:
		print("=" * 60)
		print("TRANSLATION HUB - POST-INSTALL SETUP")
		print("=" * 60)

		setup_default_settings()
		create_erpnext_pt_br_profile()

		frappe.db.commit()

		print("\n" + "=" * 60)
		print("SETUP COMPLETE!")
		print("=" * 60)
		print("\nTranslation Hub is ready to use.")
		print("Agent Pipeline is ENABLED by default.")
		print("\nNext steps:")
		print("1. Configure your API key in Translator Settings")
		print("2. Add apps to Monitored Apps")
		print("3. Create Translation Jobs")

	except Exception as e:
		print(f"Warning: Post-install setup failed: {e}")
		# Don't raise - allow installation to complete


def setup_default_settings():
	"""Configure default Translator Settings."""
	print("\n1. Configuring Translator Settings...")

	settings = frappe.get_single("Translator Settings")

	# Enable Agent Pipeline by default
	if hasattr(settings, "use_agent_pipeline"):
		settings.use_agent_pipeline = 1
		settings.quality_threshold = 0.8
		print("   ✓ Agent Pipeline enabled (quality_threshold: 0.8)")

	# Enable database storage (recommended)
	settings.use_database_storage = 1
	print("   ✓ Database storage enabled")

	settings.save(ignore_permissions=True)


def create_erpnext_pt_br_profile():
	"""Create Regional Expert Profile for ERPNext Brazilian Portuguese."""
	print("\n2. Creating Regional Expert Profile for ERPNext pt-BR...")

	profile_name = "ERPNext Brasil"

	# Check if already exists
	if frappe.db.exists("Regional Expert Profile", profile_name):
		print(f"   ✓ Profile '{profile_name}' already exists")
		return

	# Ensure pt-BR language exists
	if not frappe.db.exists("Language", "pt-BR"):
		print("   Creating pt-BR language...")
		frappe.get_doc(
			{"doctype": "Language", "language_code": "pt-BR", "language_name": "Portuguese (Brazil)"}
		).insert(ignore_permissions=True)

	# Create comprehensive Brazilian Portuguese profile for ERPNext
	profile = frappe.get_doc(
		{
			"doctype": "Regional Expert Profile",
			"profile_name": profile_name,
			"is_active": 1,
			"region": "pt-BR",
			"language": "pt-BR",
			"app": "erpnext",  # Scope to ERPNext
			"formality_level": "Formal",
			"cultural_context": """Tradução para português brasileiro formal, adequado para ambiente corporativo e sistemas ERP.

DIRETRIZES GERAIS:
- Use 'você' ao invés de 'tu'
- Prefira termos técnicos consolidados em português
- Evite gírias e regionalismos excessivos
- Mantenha consistência com terminologia contábil/fiscal brasileira

REGRAS FISCAIS BRASILEIRAS:
- 'Invoice' → 'Nota Fiscal' (NF-e, NFS-e, NFC-e conforme contexto)
- 'Tax' → 'Imposto' ou nome específico (ICMS, PIS, COFINS, ISS, IPI)
- 'VAT' → 'ICMS' em contexto de mercadorias
- 'Withholding Tax' → 'Retenção de Impostos' ou 'Impostos Retidos'
- 'Tax ID' → 'CNPJ' (empresa) ou 'CPF' (pessoa física)
- 'Fiscal Year' → 'Ano Fiscal' ou 'Exercício Fiscal'

TERMINOLOGIA CONTÁBIL:
- 'Chart of Accounts' → 'Plano de Contas'
- 'General Ledger' → 'Razão Geral' ou 'Livro Razão'
- 'Journal Entry' → 'Lançamento Contábil'
- 'Accounts Payable' → 'Contas a Pagar'
- 'Accounts Receivable' → 'Contas a Receber'

FORMATAÇÃO:
- Use vírgula como separador decimal (1.234,56)
- Use ponto como separador de milhares (1.234.567)
- Datas no formato DD/MM/AAAA""",
			"industry_jargon": """{
  "Invoice": "Nota Fiscal",
  "Sales Invoice": "Nota Fiscal de Venda",
  "Purchase Invoice": "Nota Fiscal de Compra",
  "Tax Invoice": "Nota Fiscal Eletrônica",
  "Credit Note": "Nota de Crédito",
  "Debit Note": "Nota de Débito",
  "Purchase Order": "Pedido de Compra",
  "Sales Order": "Pedido de Venda",
  "Quotation": "Orçamento",
  "Delivery Note": "Nota de Entrega",
  "Stock": "Estoque",
  "Warehouse": "Almoxarifado",
  "Supplier": "Fornecedor",
  "Customer": "Cliente",
  "Item": "Item",
  "BOM": "Lista de Materiais",
  "Work Order": "Ordem de Produção",
  "Batch": "Lote",
  "Serial No": "Número de Série",
  "Chart of Accounts": "Plano de Contas",
  "Journal Entry": "Lançamento Contábil",
  "Payment Entry": "Lançamento de Pagamento",
  "General Ledger": "Razão Geral",
  "Accounts Payable": "Contas a Pagar",
  "Accounts Receivable": "Contas a Receber",
  "Cost Center": "Centro de Custo",
  "Fiscal Year": "Ano Fiscal",
  "Tax Withholding": "Retenção de Impostos"
}""",
			"forbidden_terms": [
				{"term": "deletar", "reason": "Use 'excluir' ou 'remover'"},
				{"term": "setar", "reason": "Use 'definir' ou 'configurar'"},
				{"term": "linkar", "reason": "Use 'vincular' ou 'associar'"},
				{"term": "customizar", "reason": "Use 'personalizar'"},
				{"term": "resetar", "reason": "Use 'redefinir'"},
				{"term": "default", "reason": "Use 'padrão'"},
				{"term": "invoice", "reason": "Use 'nota fiscal' (contexto fiscal brasileiro)"},
				{"term": "you", "reason": "Traduza para 'você' (não 'tu')"},
			],
			"preferred_synonyms": [
				{
					"original_term": "invoice",
					"preferred_term": "nota fiscal",
					"context": "Documento fiscal brasileiro",
				},
				{
					"original_term": "sales invoice",
					"preferred_term": "nota fiscal de venda",
					"context": "NF-e de saída",
				},
				{
					"original_term": "purchase invoice",
					"preferred_term": "nota fiscal de compra",
					"context": "NF-e de entrada",
				},
				{
					"original_term": "credit note",
					"preferred_term": "nota de crédito",
					"context": "Devolução/correção",
				},
				{
					"original_term": "debit note",
					"preferred_term": "nota de débito",
					"context": "Correção de valor",
				},
				{
					"original_term": "purchase order",
					"preferred_term": "pedido de compra",
					"context": "Compras",
				},
				{"original_term": "sales order", "preferred_term": "pedido de venda", "context": "Vendas"},
				{
					"original_term": "quotation",
					"preferred_term": "orçamento",
					"context": "Proposta comercial",
				},
				{
					"original_term": "delivery note",
					"preferred_term": "nota de entrega",
					"context": "Logística",
				},
				{"original_term": "stock", "preferred_term": "estoque", "context": "Inventário"},
				{"original_term": "warehouse", "preferred_term": "almoxarifado", "context": "Armazenamento"},
				{"original_term": "supplier", "preferred_term": "fornecedor", "context": "Compras"},
				{"original_term": "customer", "preferred_term": "cliente", "context": "Vendas"},
				{
					"original_term": "chart of accounts",
					"preferred_term": "plano de contas",
					"context": "Contabilidade",
				},
				{
					"original_term": "journal entry",
					"preferred_term": "lançamento contábil",
					"context": "Contabilidade",
				},
				{
					"original_term": "payment entry",
					"preferred_term": "lançamento de pagamento",
					"context": "Financeiro",
				},
				{
					"original_term": "general ledger",
					"preferred_term": "razão geral",
					"context": "Contabilidade",
				},
				{
					"original_term": "accounts payable",
					"preferred_term": "contas a pagar",
					"context": "Financeiro",
				},
				{
					"original_term": "accounts receivable",
					"preferred_term": "contas a receber",
					"context": "Financeiro",
				},
				{
					"original_term": "cost center",
					"preferred_term": "centro de custo",
					"context": "Contabilidade gerencial",
				},
				{"original_term": "fiscal year", "preferred_term": "ano fiscal", "context": "Contabilidade"},
				{"original_term": "tax", "preferred_term": "imposto", "context": "Fiscal"},
			],
		}
	)

	profile.insert(ignore_permissions=True)
	print(f"   ✓ Profile '{profile_name}' created with Brazilian fiscal rules")
	print(f"      - {len(profile.forbidden_terms)} forbidden terms")
	print(f"      - {len(profile.preferred_synonyms)} preferred synonyms")


# For manual execution
if __name__ == "__main__":
	after_install()
