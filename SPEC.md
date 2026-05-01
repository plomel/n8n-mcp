# n8n MCP Server — Spec Técnica

## 1. Problema / Objetivo
Permitir ao Claude controlar o n8n (criar, editar, acionar workflows) diretamente via ferramentas MCP, sem abrir o browser. Claude torna-se o "cérebro" da automação; o n8n é o motor de execução.

## 2. Solução
MCP server Python (`n8n_mcp.py`) que expõe 10 ferramentas para interagir com a API REST do n8n local. Registado no Claude Code e Claude Desktop. Os workflows usam Groq (Llama3-70b) como LLM interno com Ollama/Gemma4 como fallback.

## 3. Arquitetura
```
n8n_mcp.py          → MCP server (padrão async with stdio_server())
    └── httpx        → chamadas REST à API n8n (localhost:5678)
    └── .env         → N8N_API_KEY + N8N_URL

n8n em Docker (localhost:5678):
    9 workflows ativos:
    ├── TB: Price Alert, Daily PnL, Risk Guardian
    ├── FAT: Invoice Scanner, Monthly Audit
    └── WG: Product Discovery, Product Upload, Price Monitor, Weekly Report

Automation-Logs/ (no Vault) → logs persistentes em markdown
```

## 4. API / Interfaces
**MCP tools disponíveis:**
| Tool | Função |
|---|---|
| `list_workflows` | Lista todos os workflows |
| `get_workflow` | Detalhes de um workflow |
| `create_workflow` | Cria novo workflow |
| `update_workflow` | Edita workflow existente |
| `delete_workflow` | Remove workflow |
| `activate_workflow` | Ativa/desativa |
| `trigger_workflow` | Aciona manualmente |
| `get_execution` | Estado de execução |
| `list_executions` | Histórico |
| `write_vault_log` | Guarda log em Obsidian |

**n8n API:** JWT em `.env` — pode expirar; regenerar em `localhost:5678 → Settings → n8n API`

## 5. Decisões Técnicas
- **MCP sobre REST direto** — Claude pode criar/editar workflows em linguagem natural sem conhecer JSON do n8n
- **Groq (Llama3-70b)** como LLM nos workflows — gratuito com tier generoso, mais rápido que Ollama
- **JWT renovável** — API key do n8n expira ao reiniciar Docker; processo documentado

## 6. Estado Atual
- ✅ MCP server funcional e registado (Claude Code + Claude Desktop)
- ✅ 9 workflows criados e ativos
- ✅ Price Alert + Risk Guardian funcionam sem credenciais (API pública Binance)
- ⏳ Gmail OAuth2 bloqueado — todos os alertas por email inoperacionais
- ⏳ Notion API + IDs — FAT-1/2 e WG-1/2/3 com placeholders

## 7. Próximos Passos
1. Configurar Gmail OAuth2 (desbloqueia 7 workflows)
2. Criar databases Notion + substituir IDs placeholders
3. Adicionar variáveis em falta: GROQ_API_KEY, SHOPIFY_ACCESS_TOKEN, CJ_ACCESS_TOKEN

## 8. Riscos / Limitações
- JWT do n8n expira ao reiniciar Docker — atualizar .env sempre que necessário
- Groq tem rate limits no tier gratuito (30 req/min)
- Docker n8n usa volume `n8n_data` — não perder este volume (contém todos os workflows)
