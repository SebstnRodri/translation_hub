"""
Consolidated script to configure the Agent Pipeline and Regional Expert Profiles.
Execute with: bench --site development.localhost execute translation_hub.setup_agent_pipeline.setup
"""

import frappe


def setup():
	"""Setup Agent Pipeline for production or testing."""

	print("=" * 60)
	print("SETUP AGENT PIPELINE")
	print("=" * 60)

	# 1. Create Regional Expert Profile for pt-BR (ERPNext/Business)
	print("\n1. Creating Regional Expert Profile pt-BR...")
	create_regional_profile()

	# 2. Enable Agent Pipeline in settings
	print("\n2. Enabling Agent Pipeline in settings...")
	enable_agent_pipeline()

	# 3. Ensure apps exist
	print("\n3. Ensuring apps exist...")
	for app in ["erpnext", "frappe"]:
		ensure_app_exists(app)

	# 4. Add as Monitored Apps
	print("\n4. Adding as Monitored Apps...")
	settings = frappe.get_single("Translator Settings")
	for app in ["erpnext", "frappe"]:
		add_monitored_app(settings, app)
	settings.save(ignore_permissions=True)

	print("\n" + "=" * 60)
	print("COMPLETED SETUP AGENT PIPELINE!")
	print("=" * 60)
	print("\nNext steps:")
	print("1. Configure your API key in Translator Settings")
	print("2. Create a Translation Job for the app desired")
	print("3. Execute the job and observe the Agent Pipeline logs")


def create_regional_profile():
	"""Create or update the Regional Expert Profile for pt-BR."""
	profile_name = "erpnext_pt-BR"

	# Ensure language exists
	language = _ensure_language_exists()

	if frappe.db.exists("Regional Expert Profile", profile_name):
		profile = frappe.get_doc("Regional Expert Profile", profile_name)
		print(f"   ✓ Updating existing profile: '{profile_name}'")
	else:
		profile = frappe.new_doc("Regional Expert Profile")
		profile.profile_name = profile_name
		print(f"   ✓ Creating new profile: '{profile_name}'")

	# Basic settings
	profile.is_active = 1
	profile.region = "pt-BR"
	profile.language = language
	profile.formality_level = "Formal"

	# Cultural context
	profile.cultural_context = """Translation to Brazilian Portuguese formal, appropriate for corporate and ERP environments.

DIRECTIVES:
- Use 'you' instead of 'you'
- Prefer consolidated technical terms in Portuguese
- Avoid excessive slang and regionalisms
- Maintain consistency with Brazilian accounting/financial terminology
- Use double quotes for citations
- Use comma as decimal separator
- Preserve placeholders exactly as they are: {}, #{}, {0}, etc.
- The term 'against' usually means association between two parties, forcing the use of 'for', 'associated with', 'referring to'.
-  """


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
  "Serial No": "Número de Série",
  "Delivery Note": "Nota de Entrega",
  "Payment Entry": "Lançamento de Pagamento",
  "Lead": "Lead",
  "Party": "Parceiro",
  "Child Company": "Filial",
  "Parent Company": "Empresa Matriz",
  "
}"""

	# Forbidden Terms
	profile.forbidden_terms = []
	forbidden = [
		("deletar", "Use 'excluir' ou 'remover'"),
		("setar", "Use 'definir' ou 'configurar'"),
		("linkar", "Use 'vincular' ou 'associar'"),
		("customizar", "Use 'personalizar'"),
		("resetar", "Use 'redefinir'"),
		("folder", "Use 'pasta'"),
		("file", "Use 'arquivo'"),
		("clicar", "Use 'clique' ou 'selecione'"),
	]
	for term, reason in forbidden:
		profile.append("forbidden_terms", {"term": term, "reason": reason})

	# Preferred Synonyms
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
		("journal entry", "lançamento contábil", "Contabilidade"),
		("general ledger", "razão geral", "Contabilidade"),
		("chart of accounts", "plano de contas", "Contabilidade"),
		("fiscal year", "ano fiscal", "Contabilidade"),
		("cost center", "centro de custo", "Contabilidade"),
		("against account", "contrapartida", "Contabilidade"),
	]
	for original, preferred, context in synonyms:
		profile.append(
			"preferred_synonyms",
			{"original_term": original, "preferred_term": preferred, "context": context},
		)

	profile.save(ignore_permissions=True)
	frappe.db.commit()

	print(f"   ✓ Profile configurated:")
	print(f"      - Forbidden Terms: {len(profile.forbidden_terms)}")
	print(f"      - Preferred Synonyms: {len(profile.preferred_synonyms)}")


def _ensure_language_exists():
	"""ensure language exists"""
	for lang_name in ["pt-BR", "Portuguese (Brazil)", "pt"]:
		if frappe.db.exists("Language", lang_name):
			return lang_name    

	# Create if not exists
	lang_doc = frappe.get_doc({
		"doctype": "Language",
		"language_code": "pt-BR",
		"language_name": "Portuguese (Brazil)",
		"enabled": 1
	})
	lang_doc.insert(ignore_permissions=True)
	print("   ✓ Idioma pt-BR created")
	return "pt-BR"


def enable_agent_pipeline():
	"""Enable agent pipeline"""
	settings = frappe.get_single("Translator Settings")

	if not hasattr(settings, "use_agent_pipeline"):
		print("   ⚠ Field 'use_agent_pipeline' not found - run 'bench migrate' first")
		return

	settings.use_agent_pipeline = 1
	settings.quality_threshold = 0.8

	# Definir perfil regional padrão
	if frappe.db.exists("Regional Expert Profile", "erpnext_pt-BR"):
		settings.default_regional_expert = "erpnext_pt-BR"

	settings.save(ignore_permissions=True)
	print(f"   ✓ Agent Pipeline enabled (threshold: {settings.quality_threshold})")
	print(f"   ✓ Default Regional Expert: {settings.default_regional_expert or 'Not defined'}")


def ensure_app_exists(app_name):
	"""Ensure app exists"""
	if frappe.db.exists("App", app_name):
		print(f"   ✓ App '{app_name}' exists")
		return True

	# Verificar se está instalado
	try:
		from frappe import get_app_path
		get_app_path(app_name)
		
		app = frappe.get_doc({
			"doctype": "App",
			"name": app_name,
			"app_name": app_name,
		})
		app.insert(ignore_permissions=True)
		print(f"   ✓ App '{app_name}' registered")
		return True
	except Exception:
		print(f"   ⚠ App '{app_name}' not installed")
		return False


def add_monitored_app(settings, app_name):
	"""Add app as Monitored App."""
	for row in settings.monitored_apps or []:
		if row.source_app == app_name:
			print(f"   ✓ '{app_name}' already monitored")
			return

	if frappe.db.exists("App", app_name):
		settings.append("monitored_apps", {"source_app": app_name})
		print(f"   ✓ '{app_name}' added as Monitored App")


# Funções auxiliares para uso individual

def create_test_job(app_name="erpnext", language="pt-BR"):
	"""Create a Translation Job for testing."""
	job_title = f"Agent Pipeline Test - {app_name} {language}"

	if frappe.db.exists("Translation Job", {"title": job_title}):
		print(f"Job '{job_title}' already exists")
		return

	job = frappe.get_doc({
		"doctype": "Translation Job",
		"title": job_title,
		"source_app": app_name,
		"target_language": language,
		"status": "Pending",
		"regional_expert_profile": "erpnext_pt-BR" if frappe.db.exists("Regional Expert Profile", "erpnext_pt-BR") else None,
	})
	job.insert(ignore_permissions=True)
	frappe.db.commit()
	print(f"✓ Translation Job created: {job_title}")


def update_profile_only():
	"""Update Regional Expert Profile (useful for refinements)."""
	create_regional_profile()
	frappe.db.commit()


if __name__ == "__main__":
	setup()
