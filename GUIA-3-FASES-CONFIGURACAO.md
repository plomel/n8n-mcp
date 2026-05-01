# Guia Completo: 3 Fases de Configuração (Gmail OAuth2 + Notion API + rclone)

**Objetivo:** Desbloquear todos os 9 workflows n8n (9 workflows aguardam estas credenciais)

**Tempo estimado:** 45 minutos total (15min cada fase)

---

## ⏱️ Timeline Rápida
- Gmail OAuth2: 15 min (Google Cloud Console → Client ID/Secret)
- Notion API Token: 5 min (Notion Settings → Internal Integration)
- rclone Google Drive: 15 min (instalação + autorização + mount)
- **Substituir IDs no .env:** 10 min

---

## Fase 1: Gmail OAuth2 (15 min)

### 1.1 Criar Projeto no Google Cloud Console

1. Ir para https://console.cloud.google.com/
2. Login com a conta Google que tem as credenciais de email (ou criar projeto em conta empresa)
3. **Criar novo projeto:**
   - Clique no dropdown "Select a Project" (topo)
   - "New Project"
   - Nome: `n8n-workflows-pt`
   - Região: Europe

### 1.2 Ativar Gmail API

1. No painel esquerdo: **APIs & Services** → **Enabled APIs & Services**
2. Clique em **+ Enable APIs and Services** (topo)
3. Procure: `Gmail API`
4. Clique em **Enable**

### 1.3 Criar OAuth 2.0 Credentials

1. **APIs & Services** → **Credentials**
2. Clique em **+ Create Credentials** (topo)
3. Escolha: **OAuth client ID**
4. Se aparecer aviso "Configure OAuth consent screen first":
   - Clique em "Configure Consent Screen"
   - User Type: **External** (recomendado para início)
   - Preencha:
     - App name: `n8n Automation`
     - User support email: `pablomaciel2003.pm@gmail.com`
     - Developer contact: `pablomaciel2003.pm@gmail.com`
   - Clique **Save and Continue**
   - Scopes: Clique **Add or Remove Scopes**
     - Procure: `gmail.send` e `gmail.readonly`
     - Selecione ambas
     - **Update** e **Save and Continue**
   - Volte para **Credentials**

5. Agora clique **+ Create Credentials** → **OAuth client ID** novamente
6. Application Type: **Desktop application**
   - Nome: `n8n-gmail-local`
   - **Create**

7. **IMPORTANTE:** Download o ficheiro JSON (botão ao lado do client ID)
   - Guarde como: `C:\Users\Ryzen 7 5700g Gamer\Documents\Claude\Obsidian_Vault One\Projects\n8n-mcp\google_oauth_credentials.json`

### 1.4 Extrair Client ID e Secret

Abra o ficheiro JSON que downloadou. Procure:

```json
{
  "installed": {
    "client_id": "COPIAR_ESTE_VALOR",
    "client_secret": "COPIAR_ESTE_VALOR",
    ...
  }
}
```

**Guarde estes valores** para colocar no `.env` depois.

---

## Fase 2: Notion API Token (5 min)

### 2.1 Criar Internal Integration no Notion

1. Ir para https://www.notion.so/my-integrations
2. Clique em **+ New integration**
3. Nome: `n8n Automation`
4. Workspace: Selecione o seu workspace
5. Clique **Submit**

### 2.2 Copiar Token

1. Página agora mostra: **Internal Integration Token**
2. Clique em **Show** (se escondido)
3. Clique **Copy token** (ou copie manualmente)

**Guarde este valor** para colocar no `.env` depois.

### 2.3 Dar Permissões ao Integration no Notion

Volte para a página do Notion onde tem as databases:

1. Abra cada database que precisa (Faturas, Produtos, Audit Log, Trades)
2. No topo direito: **Share** → **Invite**
3. Procure o integration que criou (`n8n Automation`)
4. Selecione **Can edit**
5. Repita para TODAS as databases que o n8n precisa

---

## Fase 3: rclone Google Drive (15 min)

### 3.1 Instalar rclone

```powershell
# Se tem chocolatey instalado:
choco install rclone

# Senão, descarregue de: https://rclone.org/downloads/
# Escolha: Windows amd64 (seu sistema é 64-bit)
# Descompacte para: C:\Program Files\rclone\
# Adicione ao PATH do Windows se necessário
```

Verificar instalação:
```powershell
rclone version
```

### 3.2 Configurar Google Drive com rclone

```powershell
rclone config
```

Siga os passos:

1. **New remote** → pressione `n`
2. **Name:** `gdrive` (nome do remote)
3. **Storage type:** Procure `drive` (Google Drive)
4. **Client ID:** Cole o Client ID do OAuth acima (em branco, enter se quer usar default)
5. **Client Secret:** Cole o Secret
6. **Scope:** Escolha `1` (Full access)
7. **Service Account:** Deixe em branco (enter)
8. **Edit advanced config?** Pressione `n`
9. **Authenticate using web browser?** Pressione `y`
   - Abre navegador automaticamente
   - Authorize a aplicação
   - Cópia o código que aparece
   - Cola de volta na terminal
10. **Confirm?** Pressione `y`

Verá mensagem: `Success! Config saved.`

### 3.3 Montar Google Drive (opcional, recomendado)

Se quer aceder Google Drive como unidade local em Windows:

```powershell
# Criar diretório local primeiro:
mkdir C:\GoogleDrive

# Montar (precisa de WinFsp instalado: https://winfsp.dev/)
rclone mount gdrive: C:\GoogleDrive --vfs-cache-mode full
```

Deixe este comando a correr (ou use `--daemon` para background).

Agora Google Drive aparece em File Explorer como unidade.

---

## Passo Final: Atualizar .env

Crie ou edite: `C:\Users\Ryzen 7 5700g Gamer\Documents\Claude\Obsidian_Vault One\Projects\n8n-mcp\.env`

```env
# n8n Configuration
N8N_URL=http://localhost:5678
N8N_API_KEY=<COLE_A_JWT_KEY_DO_n8n_AQUI>
N8N_VAULT_PATH=C:\Users\Ryzen 7 5700g Gamer\Documents\Claude\Obsidian_Vault One\Automation-Logs

# Gmail OAuth2
GMAIL_CLIENT_ID=<COLE_O_CLIENT_ID_DO_GOOGLE_AQUI>
GMAIL_CLIENT_SECRET=<COLE_O_CLIENT_SECRET_DO_GOOGLE_AQUI>
GMAIL_AUTHORIZED_USER=pablomaciel2003.pm@gmail.com

# Notion API
NOTION_API_KEY=<COLE_O_TOKEN_DO_NOTION_AQUI>

# Notion Database IDs (VER SECÇÃO ABAIXO PARA EXTRAIR ESTES)
NOTION_DB_FATURAS=<SUBSTITUIR_PELO_ID>
NOTION_DB_PRODUTOS=<SUBSTITUIR_PELO_ID>
NOTION_DB_AUDIT_LOG=<SUBSTITUIR_PELO_ID>
NOTION_DB_TRADES=<SUBSTITUIR_PELO_ID>

# Google Drive (rclone)
GDRIVE_MOUNT_PATH=C:\GoogleDrive
GDRIVE_REMOTE=gdrive:

# APIs de Terceiros (já configuradas ou em progresso)
GROQ_API_KEY=<configurado já?>
SHOPIFY_STORE=pid94t-wh
SHOPIFY_ACCESS_TOKEN=<obter da Shopify Admin>
CJ_ACCESS_TOKEN=<obter do CJDropshipping>
BINANCE_API_KEY=<obter da Binance API>
SCRAPER_API_KEY=<obter da ScraperAPI>
```

---

## Anexo: Como Extrair Database IDs do Notion

Vai precisar de extrair 4 IDs. Faça assim:

### Para cada database que precisa:

1. Abra a database no Notion
2. Copie o URL da barra de endereços
3. O URL tem este formato:

```
https://www.notion.so/<seu_workspace>/<DATABASE_ID>?v=<view_id>
```

O **DATABASE_ID** é a parte longa após o `/` e antes do `?`

**Exemplo real:**
```
https://www.notion.so/pablomaciel/5a1f2b3c4d5e6f7g8h9i0j1k2l3m4n5o?v=...
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                      DATABASE_ID (32 caracteres hex)
```

### Databases a extrair:

1. **NOTION_DB_FATURAS** → Database "Faturas" (projeto Rosa Dos Leitões)
2. **NOTION_DB_PRODUTOS** → Database "Produtos" (projeto WorkGadget)
3. **NOTION_DB_AUDIT_LOG** → Database "Audit Log" (projeto Faturas)
4. **NOTION_DB_TRADES** → Database "Trades" (projeto trading-bot)

Cole os 4 IDs no `.env` acima.

---

## Verificação Final

Depois de completar as 3 fases + preencher `.env`:

```powershell
# Testar Gmail
python C:\Users\Ryzen 7 5700g Gamer\Documents\Claude\Obsidian_Vault One\Projects\n8n-mcp\test_gmail_oauth.py

# Testar Notion
python C:\Users\Ryzen 7 5700g Gamer\Documents\Claude\Obsidian_Vault One\Projects\n8n-mcp\test_notion_api.py

# Testar rclone
rclone ls gdrive:

# Restart n8n MCP
# No Claude Code: desligar e ligar o MCP server
```

Depois de tudo a verde, os 9 workflows no n8n devem estar totalmente funcionais.

---

**Criado:** 2026-04-17 · **Para:** Pablo Maciel · **Status:** Pronto para execução
