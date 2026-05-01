# n8n MCP Server — Guia para Claude Code

## Visão Geral

MCP server Python que permite ao Claude Code e Claude Desktop controlarem o n8n localmente.
Claude é o cérebro: cria, edita e acciona workflows. O n8n executa-os.
Groq (Llama3-70b) é o LLM dentro dos workflows. Gemma4:e4b local é o fallback.

## Stack

- `n8n_mcp.py` — MCP server (padrão idêntico ao binance_mcp.py)
- `n8n` em Docker — motor de execução em `localhost:5678`
- `httpx` — chamadas à API REST do n8n
- `Automation-Logs/` no Vault — memória persistente em markdown

## Ferramentas MCP disponíveis

| Ferramenta | Função |
|---|---|
| `list_workflows` | Lista todos os workflows |
| `get_workflow` | Detalhes de um workflow |
| `create_workflow` | Cria novo workflow |
| `update_workflow` | Edita workflow existente |
| `delete_workflow` | Remove workflow |
| `activate_workflow` | Activa/desactiva workflow |
| `trigger_workflow` | Acciona workflow manualmente |
| `get_execution` | Estado de uma execução |
| `list_executions` | Histórico de execuções |
| `write_vault_log` | Guarda log em Automation-Logs/ |

## Setup Inicial (uma vez)

### 1. Arrancar n8n em Docker
```powershell
docker run -d `
  --name n8n `
  --restart unless-stopped `
  -p 5678:5678 `
  -v n8n_data:/home/node/.n8n `
  docker.n8n.io/n8nio/n8n
```

### 2. Configurar n8n
1. Abrir `http://localhost:5678`
2. Criar conta local
3. Settings → API → Enable API → copiar a key

### 3. Criar .env
```
cp .env.example .env
# editar .env e colocar a API key do n8n
```

### 4. Instalar dependências
```
pip install -r requirements.txt
```

### 5. Testar
```
python n8n_mcp.py
# deve mostrar: ✅ n8n MCP Server a arrancar...
```

## Registo no Claude Code

Adicionar em `C:\Users\Ryzen 7 5700g Gamer\.claude\settings.json` dentro de `mcpServers`:
```json
"n8n": {
  "command": "python",
  "args": ["C:\\Users\\Ryzen 7 5700g Gamer\\Documents\\Claude\\Obsidian_Vault One\\Projects\\n8n-mcp\\n8n_mcp.py"]
}
```

## Registo no Claude Desktop

Adicionar em `C:\Users\Ryzen 7 5700g Gamer\AppData\Roaming\Claude\claude_desktop_config.json` dentro de `mcpServers`:
```json
"n8n": {
  "command": "python",
  "args": ["C:\\Users\\RYZEN7~1\\DOCUME~1\\Claude\\OBSIDI~1\\Projects\\n8n-mcp\\n8n_mcp.py"]
}
```
Reiniciar Claude Desktop após editar.

## Modelos nos Workflows n8n

- **Groq (primário):** Settings → Credentials → Header Auth → `Authorization: Bearer <groq_key>`
  - Endpoint: `https://api.groq.com/openai/v1/chat/completions`
  - Modelos recomendados: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`
- **Ollama (fallback):** `http://localhost:11434/api/generate` — sem autenticação
  - Modelo: `gemma4:e4b`

## Referências

- `Projects/trading-bot/binance_mcp.py` — padrão MCP que este ficheiro segue
- `Automation-Logs/` — logs de execução (criados automaticamente)
- n8n API docs: `http://localhost:5678/api/v1/docs` (disponível quando n8n está a correr)

---

## Claude Context

> Secção mantida automaticamente pelo Claude. Última atualização: 2026-04-16

### Estado atual
- ✅ Docker n8n a correr em `localhost:5678`
- ✅ `.env` configurado com `N8N_API_KEY` (JWT) e `N8N_URL`
- ✅ Dependências instaladas (`mcp==1.27.0`, `httpx`, `python-dotenv`)
- ✅ Bug corrigido: `stdio_server` é async context manager em mcp>=1.0
- ✅ Servidor registado em `.claude/settings.json` e `claude_desktop_config.json`
- ✅ **9 workflows criados e ativos** (2026-04-16)

### Nota sobre a API Key
A API key é um JWT gerado pelo n8n. Pode expirar ou ser invalidada ao reiniciar o n8n. Se der 401, ir a `localhost:5678 → Settings → n8n API` e gerar nova key → atualizar `.env`.

### Workflows ativos (9 total)
TB: Price Alert (5min), Daily PnL (18h), Risk Guardian (15min) · FAT: Invoice Scanner (08h), Monthly Audit (1º mês) · WG: Product Discovery (09h), Product Upload (webhook), Price Monitor (6h), Weekly Report (domingo 20h)

### Bloqueios ativos
- **Gmail OAuth2** — necessário para email alerts (todos os projetos)
- **Notion API + IDs** — FAT-1/2, WG-1/2/3, TB-2 (substituir placeholders `SUBSTITUIR_PELO_ID_DATABASE_*`)
- **Variables em falta:** `GROQ_API_KEY`, `SHOPIFY_STORE`, `SHOPIFY_ACCESS_TOKEN`, `CJ_ACCESS_TOKEN`, `BINANCE_API_KEY`, `SCRAPER_API_KEY`

### Nota técnica MCP
`stdio_server` em mcp>=1.0 é async context manager (não coroutine). Padrão correto em `n8n_mcp.py` e `binance_mcp.py`.
