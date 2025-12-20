"""
Script para popular o Regional Expert Profile com dados de contexto.
Execute: bench --site development.localhost execute translation_hub.populate_profile.run
"""

import frappe


def run():
	"""Popula o Regional Expert Profile erpnext_pt-BR com dados de contexto."""
	profile_name = "erpnext_pt-BR"

	if not frappe.db.exists("Regional Expert Profile", profile_name):
		print(f"Profile {profile_name} não encontrado!")
		return

	profile = frappe.get_doc("Regional Expert Profile", profile_name)

	# Cultural Context
	profile.cultural_context = """Tradução para português brasileiro formal, adequado para ambiente corporativo e sistemas ERP.

DIRETRIZES:
- Use 'você' ao invés de 'tu'
- Prefira termos técnicos consolidados em português
- Evite gírias e regionalismos excessivos
- Mantenha consistência com terminologia contábil/fiscal brasileira
- Use aspas duplas para citações
- Use vírgula como separador decimal"""

	# Industry Jargon (JSON)
	profile.industry_jargon = """{
  "Invoice": "Fatura",
  "Purchase Order": "Pedido de Compra",
  "Sales Order": "Pedido de Venda",
  "Quotation": "Orçamento",
  "Stock": "Estoque",
  "Warehouse": "Almoxarifado",
  "Supplier": "Fornecedor",
  "Customer": "Cliente",
  "Item": "Item",
  "BOM": "Lista de Materiais",
  "Batch": "Lote",
  "Serial No": "Número de Série"
}"""

	# Formality Level
	profile.formality_level = "Formal"

	# Clear existing and add forbidden terms
	profile.forbidden_terms = []
	forbidden = [
		("deletar", "Use 'excluir' ou 'remover'"),
		("setar", "Use 'definir' ou 'configurar'"),
		("linkar", "Use 'vincular' ou 'associar'"),
		("customizar", "Use 'personalizar'"),
		("resetar", "Use 'redefinir'"),
	]
	for term, reason in forbidden:
		profile.append("forbidden_terms", {"term": term, "reason": reason})

	# Clear existing and add preferred synonyms
	profile.preferred_synonyms = []
	synonyms = [
		("invoice", "fatura", "Documento fiscal"),
		("purchase order", "pedido de compra", "Compras"),
		("sales order", "pedido de venda", "Vendas"),
		("quotation", "orçamento", "Vendas"),
		("stock", "estoque", "Inventário"),
		("warehouse", "almoxarifado", "Armazenamento"),
		("supplier", "fornecedor", "Compras"),
		("customer", "cliente", "Vendas"),
		("delivery note", "nota de entrega", "Logística"),
		("payment entry", "lançamento de pagamento", "Financeiro"),
	]
	for original, preferred, context in synonyms:
		profile.append(
			"preferred_synonyms", {"original_term": original, "preferred_term": preferred, "context": context}
		)

	profile.save(ignore_permissions=True)
	frappe.db.commit()

	print("✓ Regional Expert Profile atualizado!")
	print(f"  - Cultural Context: {len(profile.cultural_context)} caracteres")
	print(f"  - Industry Jargon: {len(profile.industry_jargon)} caracteres")
	print(f"  - Forbidden Terms: {len(profile.forbidden_terms)} termos")
	print(f"  - Preferred Synonyms: {len(profile.preferred_synonyms)} sinônimos")
