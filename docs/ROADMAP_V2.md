# Translation Hub v2 Roadmap

> 🌐 **Language / Idioma:** [English](#english) | [Português](#português)

---

<a name="english"></a>
## 🇬🇧 English

### Vision: Translation Intelligence

Transform Translation Hub from a simple AI translation tool into an **intelligent translation platform** that deeply understands Frappe/ERPNext applications and produces translations of excellence.

---

### Phase 0: Community Engagement (Current)

**Goals:**
- Validate the vision with the Frappe/ERPNext community
- Find contributors and early adopters
- Gather feedback on priorities

**Actions:**
1. **Publish RFC** on [discuss.frappe.io](https://discuss.frappe.io)
2. **Demo Video** showing v1 capabilities + v2 vision
3. **GitHub Discussions** with roadmap and milestones
4. **Community Channels**: Telegram, Discord, LinkedIn

---

### Phase 1: Translation Quality Analysis

- **PO Analyzer**: Scan `.po` files for quality issues
- **Inconsistency Detector**: Find terms translated differently
- **Quality Score**: Rate translation quality per file

---

### Phase 2: Deep Context Understanding (Completed - RC 2.0)

- ✅ **DocType Parser**: (Replaced by `Localization Profile` and `Translation Domain`)
- ✅ **Code Analyzer**: (Implemented via `Context Rules` Regex)
- ✅ **Auto-Glossary**: System now suggests terms based on rejections (`Term Rejection Pattern`)

---

### Phase 3: Iterative Excellence (Completed - RC 2.0)

- ✅ **Self-Review**: Implemented `auto_review()` based on profiles
- ✅ **Consistency Check**: Enforced via `Translation Domain` glossary injection
- ✅ **Human-in-the-Loop**: Full "Review -> Rejection -> Task" workflow

---

### Phase 4: Community Sharing (Next Steps - v3.0)

- **Translation Registry**: Central repo for community translations
- **Quality Badges**: Verified, Reviewed, AI-Generated
- **Pull Requests**: Contribute back to official repos

---

### Timeline

| Phase | Target | Status |
|-------|--------|--------|
| 0: Community | Dec 2025 | ✅ Done |
| 1: Analysis | Jan 2026 | ✅ Done (via Reviews) |
| 2: Context (RC 2.0) | Feb 2026 | ✅ Done |
| 3: Excellence (RC 2.0) | Mar 2026 | ✅ Done |
| 4: Sharing (v3.0) | Apr 2026 | 📋 Planned |

---

### Get Involved

⭐ Star the repo: [github.com/SebstnRodri/translation_hub](https://github.com/SebstnRodri/translation_hub)

---

<a name="português"></a>
## 🇧🇷 Português

### Visão: Inteligência em Tradução

Transformar o Translation Hub de uma simples ferramenta de tradução com IA em uma **plataforma inteligente** que compreende profundamente as aplicações Frappe/ERPNext e produz traduções de excelência.

---

### Fase 0: Engajamento da Comunidade (Atual)

**Objetivos:**
- Validar a visão com a comunidade Frappe/ERPNext
- Encontrar contribuidores e early adopters
- Coletar feedback sobre prioridades

**Ações:**
1. **Publicar RFC** no [discuss.frappe.io](https://discuss.frappe.io)
2. **Vídeo Demo** mostrando capacidades v1 + visão v2
3. **GitHub Discussions** com roadmap e milestones
4. **Canais da Comunidade**: Telegram, Discord, LinkedIn

---

### Fase 1: Análise de Qualidade de Traduções

- **Analisador de PO**: Varrer arquivos `.po` por problemas de qualidade
- **Detector de Inconsistências**: Encontrar termos traduzidos diferentemente
- **Score de Qualidade**: Avaliar qualidade por arquivo

---

### Fase 2: Compreensão Profunda de Contexto

- **Parser de DocTypes**: Extrair contexto de campos do JSON
- **Analisador de Código**: Ler docstrings e comentários Python
- **Glossário Automático**: Construir glossário a partir do código

---

### Fase 3: Excelência Iterativa

- **Auto-Revisão**: IA revisa suas próprias traduções
- **Verificação de Consistência**: Mesmo termo = mesma tradução
- **Human-in-the-Loop**: Fila de revisão para traduções incertas

---

### Fase 4: Compartilhamento na Comunidade

- **Registro de Traduções**: Repositório central para traduções da comunidade
- **Selos de Qualidade**: Verificado, Revisado, Gerado por IA
- **Pull Requests**: Contribuir de volta para repos oficiais

---

### Cronograma

| Fase | Previsão | Status |
|------|----------|--------|
| 0: Comunidade | Dez 2025 | 🔄 Em Progresso |
| 1: Análise | Jan 2026 | 📋 Planejado |
| 2: Contexto | Fev 2026 | 📋 Planejado |
| 3: Excelência | Mar 2026 | 📋 Planejado |
| 4: Compartilhamento | Abr 2026 | 📋 Planejado |

---

### Participe

⭐ Dê uma estrela no repo: [github.com/SebstnRodri/translation_hub](https://github.com/SebstnRodri/translation_hub)
