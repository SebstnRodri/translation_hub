"""
Script para configurar o setup completo do Agent Pipeline para teste com ERPNext.
Execute com: bench execute translation_hub.setup_agent_test.setup
"""

import frappe


def setup():
	"""Cria setup completo para testar o Agent Pipeline com ERPNext."""

	print("=" * 60)
	print("SETUP DO AGENT PIPELINE PARA TESTE")
	print("=" * 60)

	# 1. Criar Regional Expert Profile para pt-BR
	print("\n1. Criando Regional Expert Profile pt-BR...")
	create_regional_profile()

	# 2. Habilitar Agent Pipeline nas configurações
	print("\n2. Habilitando Agent Pipeline nas configurações...")
	enable_agent_pipeline()

	# 3. Criar um App entry para erpnext se não existir
	print("\n3. Verificando App entry para erpnext...")
	ensure_app_exists("erpnext")

	# 4. Adicionar erpnext como Monitored App
	print("\n4. Adicionando erpnext como Monitored App...")
	add_monitored_app("erpnext")

	# 5. Criar Translation Job para teste
	print("\n5. Criando Translation Job para ERPNext...")
	create_test_job()

	print("\n" + "=" * 60)
	print("SETUP COMPLETO!")
	print("=" * 60)
	print("\nPróximos passos:")
	print("1. Configure sua API key em Translator Settings (Gemini, Groq ou OpenRouter)")
	print("2. Execute o Translation Job criado: 'Test Agent Pipeline - ERPNext pt-BR'")
	print("3. Observe os logs para ver os 3 agentes trabalhando")
	print("4. Verifique Translation Review para traduções de baixa qualidade")


def create_regional_profile():
	"""Cria ou atualiza o Regional Expert Profile para pt-BR."""
	profile_name = "pt-BR Business"

	if frappe.db.exists("Regional Expert Profile", profile_name):
		print(f"   ✓ Regional Expert Profile '{profile_name}' já existe")
		return

	# Verificar se o idioma pt-BR existe
	language = None
	for lang_name in ["pt-BR", "Portuguese (Brazil)", "pt"]:
		if frappe.db.exists("Language", lang_name):
			language = lang_name
			break

	if not language:
		print("   ⚠ Idioma português não encontrado, criando...")
		lang_doc = frappe.get_doc(
			{"doctype": "Language", "language_code": "pt-BR", "language_name": "Portuguese (Brazil)"}
		)
		lang_doc.insert(ignore_permissions=True)
		language = "pt-BR"

	profile = frappe.get_doc(
		{
			"doctype": "Regional Expert Profile",
			"profile_name": profile_name,
			"is_active": 1,
			"region": "pt-BR",
			"language": language,
			"formality_level": "Formal",
			"cultural_context": """Tradução para português brasileiro formal, adequado para ambiente corporativo e sistemas ERP.

DIRETRIZES:
- Use 'você' ao invés de 'tu'
- Prefira termos técnicos consolidados em português (ex: 'pedido de venda' ao invés de 'ordem de venda')
- Evite gírias e regionalismos excessivos
- Mantenha consistência com terminologia contábil/fiscal brasileira
- Use aspas duplas para citações
- Use vírgula como separador decimal""",
			"forbidden_terms": [
				{"term": "deletar", "reason": "Use 'excluir' ou 'remover'"},
				{"term": "setar", "reason": "Use 'definir' ou 'configurar'"},
				{"term": "linkar", "reason": "Use 'vincular' ou 'associar'"},
				{"term": "customizar", "reason": "Use 'personalizar'"},
			],
			"preferred_synonyms": [
				{"original_term": "invoice", "preferred_term": "fatura", "context": "Documento fiscal"},
				{
					"original_term": "purchase order",
					"preferred_term": "pedido de compra",
					"context": "Compras",
				},
				{"original_term": "sales order", "preferred_term": "pedido de venda", "context": "Vendas"},
				{"original_term": "quotation", "preferred_term": "orçamento", "context": "Vendas"},
				{"original_term": "stock", "preferred_term": "estoque", "context": "Inventário"},
				{"original_term": "warehouse", "preferred_term": "almoxarifado", "context": "Armazenamento"},
				{"original_term": "supplier", "preferred_term": "fornecedor", "context": "Compras"},
				{"original_term": "customer", "preferred_term": "cliente", "context": "Vendas"},
			],
		}
	)
	profile.insert(ignore_permissions=True)
	print(f"   ✓ Regional Expert Profile '{profile_name}' criado com sucesso")


def enable_agent_pipeline():
	"""Habilita o Agent Pipeline nas configurações do Translator."""
	settings = frappe.get_single("Translator Settings")

	# Verificar se o campo existe
	if not hasattr(settings, "use_agent_pipeline"):
		print("   ⚠ Campo 'use_agent_pipeline' não encontrado - rode 'bench migrate' primeiro")
		return

	settings.use_agent_pipeline = 1
	settings.quality_threshold = 0.8

	# Definir perfil regional padrão
	if frappe.db.exists("Regional Expert Profile", "pt-BR Business"):
		settings.default_regional_expert = "pt-BR Business"

	settings.save(ignore_permissions=True)
	print(f"   ✓ Agent Pipeline habilitado (threshold: {settings.quality_threshold})")
	print(f"   ✓ Default Regional Expert: {settings.default_regional_expert or 'Não definido'}")


def ensure_app_exists(app_name):
	"""Garante que o App existe no sistema."""
	if frappe.db.exists("App", app_name):
		print(f"   ✓ App '{app_name}' já existe")
		return

	# Criar App entry
	app = frappe.get_doc(
		{
			"doctype": "App",
			"name": app_name,
			"app_name": app_name,
		}
	)
	app.insert(ignore_permissions=True)
	print(f"   ✓ App '{app_name}' criado")


def add_monitored_app(app_name):
	"""Adiciona o app como Monitored App no Translator Settings."""
	settings = frappe.get_single("Translator Settings")

	# Verificar se já está na lista
	for row in settings.monitored_apps or []:
		if row.source_app == app_name:
			print(f"   ✓ App '{app_name}' já está em Monitored Apps")
			return

	# Adicionar à lista
	settings.append(
		"monitored_apps",
		{
			"source_app": app_name,
		},
	)
	settings.save(ignore_permissions=True)
	print(f"   ✓ App '{app_name}' adicionado como Monitored App")


def create_test_job():
	"""Cria um Translation Job de teste para ERPNext."""
	job_title = "Test Agent Pipeline - ERPNext pt-BR"

	# Verificar se já existe
	if frappe.db.exists("Translation Job", job_title):
		print(f"   ✓ Translation Job '{job_title}' já existe")
		return

	# Verificar se erpnext existe como App
	if not frappe.db.exists("App", "erpnext"):
		# Tentar Installed App
		if frappe.db.exists("Installed App", "erpnext"):
			source_app = "erpnext"
		else:
			print("   ⚠ App 'erpnext' não encontrado, pulando criação do job")
			return
	else:
		source_app = "erpnext"

	# Verificar idioma
	language = None
	for lang_name in ["pt-BR", "Portuguese (Brazil)", "pt"]:
		if frappe.db.exists("Language", lang_name):
			language = lang_name
			break

	if not language:
		print("   ⚠ Idioma português não encontrado")
		return

	job = frappe.get_doc(
		{
			"doctype": "Translation Job",
			"title": job_title,
			"source_app": source_app,
			"target_language": language,
			"status": "Pending",
			"regional_expert_profile": "pt-BR Business"
			if frappe.db.exists("Regional Expert Profile", "pt-BR Business")
			else None,
		}
	)
	job.insert(ignore_permissions=True)
	print(f"   ✓ Translation Job '{job_title}' criado")
	print(f"      - Source App: {source_app}")
	print(f"      - Target Language: {language}")
	print(f"      - Regional Expert: {job.regional_expert_profile or 'Default'}")


if __name__ == "__main__":
	setup()
