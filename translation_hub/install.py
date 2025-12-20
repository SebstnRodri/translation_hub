import json
import os

import frappe


def after_install():
	setup_localization()
	setup_agent_pipeline()


def after_migrate():
	setup_localization()


def setup_localization():
	"""
	Sets up initial Translation Domains and Localization Profiles from JSON.
	Idempotent: Checks if records exist before creating.
	"""
	print("Setting up Localization Data...")
	try:
		data = load_initial_data()

		# 1. Create Domains
		for domain_data in data.get("Translation Domain", []):
			create_domain(domain_data)

		# 2. Create Profiles
		for profile_data in data.get("Localization Profile", []):
			create_profile(profile_data)

		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Error setup_localization: {e}")
		print(f"Error setting up localization: {e}")


def load_initial_data():
	file_path = os.path.join(os.path.dirname(__file__), "setup", "initial_data.json")
	with open(file_path) as f:
		return json.load(f)


def create_domain(data):
	if not frappe.db.exists("Translation Domain", data["domain_name"]):
		doc = frappe.get_doc({"doctype": "Translation Domain"})
		doc.update(data)
		doc.insert(ignore_permissions=True)
		print(f"Created Translation Domain: {data['domain_name']}")


def create_profile(data):
	profile_name = data.get("profile_name")
	if frappe.db.exists("Localization Profile", profile_name):
		return

	# Prepare doc data
	country_code = data.pop("country_code", None)
	language_code = data.pop("language_code", None)

	doc = frappe.get_doc({"doctype": "Localization Profile"})
	doc.update(data)

	# Validate and set Country
	if country_code:
		if frappe.db.exists("Country", country_code):
			doc.country = country_code
		# Fallback for Brasil vs Brazil if needed
		elif country_code == "Brazil" and frappe.db.exists("Country", "Brasil"):
			doc.country = "Brasil"

	# Validate and set Language
	if language_code:
		if frappe.db.exists("Language", {"language_code": language_code}):
			doc.language = language_code
		else:
			print(f"Warning: Language {language_code} not found. Skipping language field for {profile_name}.")

	doc.insert(ignore_permissions=True)
	print(f"Created Localization Profile: {profile_name}")


def setup_agent_pipeline():
	"""
	Sets up the Agent Pipeline with default configuration.
	- Enables Agent Pipeline in Translator Settings
	- Creates Regional Expert Profile for ERPNext pt-BR with Brazilian fiscal rules
	"""
	print("Setting up Agent Pipeline...")
	try:
		_setup_agent_settings()
		_create_erpnext_pt_br_profile()
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Error setup_agent_pipeline: {e}")
		print(f"Error setting up Agent Pipeline: {e}")


def _setup_agent_settings():
	"""Enable Agent Pipeline in Translator Settings."""
	settings = frappe.get_single("Translator Settings")

	if hasattr(settings, "use_agent_pipeline"):
		settings.use_agent_pipeline = 1
		settings.quality_threshold = 0.8
		settings.save(ignore_permissions=True)
		print("  ✓ Agent Pipeline enabled (threshold: 0.8)")
	else:
		print("  ⚠ Agent Pipeline fields not found - run bench migrate first")


def _create_erpnext_pt_br_profile():
	"""Create Regional Expert Profile for ERPNext Brazilian Portuguese."""
	profile_name = "ERPNext Brasil"

	if frappe.db.exists("Regional Expert Profile", profile_name):
		print(f"  ✓ Profile '{profile_name}' already exists")
		return

	# Ensure pt-BR language exists
	if not frappe.db.exists("Language", "pt-BR"):
		frappe.get_doc(
			{"doctype": "Language", "language_code": "pt-BR", "language_name": "Portuguese (Brazil)"}
		).insert(ignore_permissions=True)

	# Create comprehensive Brazilian Portuguese profile
	profile = frappe.get_doc(
		{
			"doctype": "Regional Expert Profile",
			"profile_name": profile_name,
			"is_active": 1,
			"region": "pt-BR",
			"language": "pt-BR",
			"app": "erpnext",
			"formality_level": "Formal",
			"cultural_context": """Tradução para português brasileiro formal, adequado para ambiente corporativo e sistemas ERP.

REGRAS FISCAIS BRASILEIRAS:
- 'Invoice' → 'Nota Fiscal' (NF-e, NFS-e, NFC-e conforme contexto)
- 'Tax' → 'Imposto' ou nome específico (ICMS, PIS, COFINS, ISS, IPI)
- 'Tax ID' → 'CNPJ' (empresa) ou 'CPF' (pessoa física)

TERMINOLOGIA CONTÁBIL:
- 'Chart of Accounts' → 'Plano de Contas'
- 'General Ledger' → 'Razão Geral'
- 'Journal Entry' → 'Lançamento Contábil'

FORMATAÇÃO:
- Use vírgula como separador decimal (1.234,56)
- Datas no formato DD/MM/AAAA""",
			"industry_jargon": '{"Invoice": "Nota Fiscal", "Sales Invoice": "Nota Fiscal de Venda", "Purchase Invoice": "Nota Fiscal de Compra", "Purchase Order": "Pedido de Compra", "Sales Order": "Pedido de Venda", "Quotation": "Orçamento", "Stock": "Estoque", "Warehouse": "Almoxarifado", "Supplier": "Fornecedor", "Customer": "Cliente", "Chart of Accounts": "Plano de Contas", "Journal Entry": "Lançamento Contábil"}',
			"forbidden_terms": [
				{"term": "deletar", "reason": "Use 'excluir' ou 'remover'"},
				{"term": "setar", "reason": "Use 'definir' ou 'configurar'"},
				{"term": "linkar", "reason": "Use 'vincular' ou 'associar'"},
				{"term": "customizar", "reason": "Use 'personalizar'"},
			],
			"preferred_synonyms": [
				{
					"original_term": "invoice",
					"preferred_term": "nota fiscal",
					"context": "Documento fiscal brasileiro",
				},
				{
					"original_term": "purchase order",
					"preferred_term": "pedido de compra",
					"context": "Compras",
				},
				{"original_term": "sales order", "preferred_term": "pedido de venda", "context": "Vendas"},
				{"original_term": "quotation", "preferred_term": "orçamento", "context": "Vendas"},
				{"original_term": "stock", "preferred_term": "estoque", "context": "Inventário"},
				{"original_term": "warehouse", "preferred_term": "almoxarifado", "context": "Armazenamento"},
				{
					"original_term": "chart of accounts",
					"preferred_term": "plano de contas",
					"context": "Contabilidade",
				},
			],
		}
	)

	profile.insert(ignore_permissions=True)
	print(f"  ✓ Profile '{profile_name}' created with Brazilian fiscal rules")
