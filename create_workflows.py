"""
create_workflows.py — Cria os workflows iniciais no n8n via API REST
Correr: python create_workflows.py
"""

import json
import httpx
import uuid

N8N_URL = "http://localhost:5678"
N8N_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwYzRmNjk2ZC00NzBlLTRjMTMtYjE4NC1hYjA3MmNmNGQ2YjAiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiYzA5N2ZkZDktMTlhZC00ZTM0LWIzOTEtYzU2Y2IzZGUzNGJkIiwiaWF0IjoxNzc2MzAzMTEyfQ.LdaFfr5SnE5wpEIgiLfICpzGtpMX6jTGJDSsmz437XE"
HEADERS = {
    "X-N8N-API-KEY": N8N_KEY,
    "Content-Type": "application/json",
}


def uid():
    return str(uuid.uuid4())


def create_workflow(workflow: dict) -> dict:
    r = httpx.post(f"{N8N_URL}/api/v1/workflows", headers=HEADERS, json=workflow, timeout=30)
    r.raise_for_status()
    data = r.json()
    wf_id = data["id"]
    # Activar workflow
    httpx.patch(f"{N8N_URL}/api/v1/workflows/{wf_id}/activate", headers=HEADERS, timeout=30)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# TB-1: BTC/ETH Price Alert (cada 5 minutos)
# Binance public API → check thresholds → Notion log → Gmail alert
# ─────────────────────────────────────────────────────────────────────────────
def workflow_tb1_price_alert():
    n_schedule = uid()
    n_btc      = uid()
    n_eth      = uid()
    n_code     = uid()
    n_if       = uid()
    n_notion   = uid()
    n_gmail    = uid()

    return {
        "name": "[TB] Price Alert — BTC/ETH",
        "nodes": [
            {
                "id": n_schedule,
                "name": "Every 5 min",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 300],
                "parameters": {
                    "rule": {"interval": [{"field": "minutes", "minutesInterval": 5}]}
                },
            },
            {
                "id": n_btc,
                "name": "GET BTC Price",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [220, 200],
                "parameters": {
                    "method": "GET",
                    "url": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
                    "options": {},
                },
            },
            {
                "id": n_eth,
                "name": "GET ETH Price",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [220, 400],
                "parameters": {
                    "method": "GET",
                    "url": "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT",
                    "options": {},
                },
            },
            {
                "id": n_code,
                "name": "Check Thresholds",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [460, 300],
                "parameters": {
                    "mode": "runOnceForAllItems",
                    "jsCode": """
// Dados dos nós anteriores
const btcData = $('GET BTC Price').first().json;
const ethData = $('GET ETH Price').first().json;

const btc = parseFloat(btcData.price);
const eth = parseFloat(ethData.price);
const now = new Date().toISOString();

// Thresholds — ajusta conforme necessário
const alerts = [];

if (btc > 100000) alerts.push(`🚀 BTC acima de $100k! Preço atual: $${btc.toFixed(0)}`);
if (btc < 75000)  alerts.push(`⚠️ BTC abaixo de $75k! Preço atual: $${btc.toFixed(0)}`);
if (eth > 4000)   alerts.push(`🚀 ETH acima de $4k! Preço atual: $${eth.toFixed(2)}`);
if (eth < 1500)   alerts.push(`⚠️ ETH abaixo de $1.5k! Preço atual: $${eth.toFixed(2)}`);

return [{
  json: {
    btc,
    eth,
    timestamp: now,
    hasAlert: alerts.length > 0,
    alertMessage: alerts.join('\\n'),
    logEntry: `${now} | BTC: $${btc.toFixed(0)} | ETH: $${eth.toFixed(2)} | Alertas: ${alerts.length}`
  }
}];
""",
                },
            },
            {
                "id": n_if,
                "name": "Has Alert?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "position": [700, 300],
                "parameters": {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                        "conditions": [
                            {
                                "leftValue": "={{ $json.hasAlert }}",
                                "rightValue": True,
                                "operator": {"type": "boolean", "operation": "equals"},
                            }
                        ],
                        "combinator": "and",
                    }
                },
            },
            {
                "id": n_notion,
                "name": "Log to Notion",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [940, 200],
                "parameters": {
                    "method": "POST",
                    "url": "https://api.notion.com/v1/pages",
                    "authentication": "predefinedCredentialType",
                    "nodeCredentialType": "notionApi",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "Notion-Version", "value": "2022-06-28"}
                        ]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"parent\": { \"database_id\": \"SUBSTITUIR_PELO_ID_DA_DATABASE_TRADING\" },\n  \"properties\": {\n    \"Name\": { \"title\": [{ \"text\": { \"content\": \"Price Alert\" } }] },\n    \"BTC\": { \"number\": {{ $json.btc }} },\n    \"ETH\": { \"number\": {{ $json.eth }} },\n    \"Alert\": { \"rich_text\": [{ \"text\": { \"content\": \"{{ $json.alertMessage }}\" } }] },\n    \"Timestamp\": { \"date\": { \"start\": \"{{ $json.timestamp }}\" } }\n  }\n}",
                    "options": {},
                },
            },
            {
                "id": n_gmail,
                "name": "Gmail Alert",
                "type": "n8n-nodes-base.gmail",
                "typeVersion": 2.1,
                "position": [940, 400],
                "parameters": {
                    "operation": "send",
                    "sendTo": "pablomaciel2003.pm@gmail.com",
                    "subject": "=🚨 Price Alert — {{ $json.alertMessage.split('\\n')[0] }}",
                    "emailType": "text",
                    "message": "={{ $json.alertMessage }}\\n\\nBTC: ${{ $json.btc.toFixed(0) }}\\nETH: ${{ $json.eth.toFixed(2) }}\\nTimestamp: {{ $json.timestamp }}",
                    "options": {},
                },
                "credentials": {"gmailOAuth2": {"id": "gmail-credential", "name": "Gmail OAuth2"}},
            },
        ],
        "connections": {
            "Every 5 min": {
                "main": [[{"node": "GET BTC Price", "type": "main", "index": 0},
                           {"node": "GET ETH Price", "type": "main", "index": 0}]]
            },
            "GET BTC Price": {"main": [[{"node": "Check Thresholds", "type": "main", "index": 0}]]},
            "GET ETH Price": {"main": [[{"node": "Check Thresholds", "type": "main", "index": 0}]]},
            "Check Thresholds": {"main": [[{"node": "Has Alert?", "type": "main", "index": 0}]]},
            "Has Alert?": {
                "main": [
                    [{"node": "Log to Notion", "type": "main", "index": 0},
                     {"node": "Gmail Alert",   "type": "main", "index": 0}],
                    []  # false branch — nada
                ]
            },
        },
        "settings": {"executionOrder": "v1"},
    }


# ─────────────────────────────────────────────────────────────────────────────
# FAT-1: Invoice Scanner (diário às 08:00)
# Gmail search faturas → Google Drive save → Notion record
# ─────────────────────────────────────────────────────────────────────────────
def workflow_fat1_invoice_scanner():
    n_schedule  = uid()
    n_gmail     = uid()
    n_splitout  = uid()
    n_code      = uid()
    n_notion    = uid()

    return {
        "name": "[FAT] Invoice Scanner — Diário",
        "nodes": [
            {
                "id": n_schedule,
                "name": "Daily 08:00",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 300],
                "parameters": {
                    "rule": {
                        "interval": [{"field": "cronExpression", "expression": "0 8 * * *"}]
                    }
                },
            },
            {
                "id": n_gmail,
                "name": "Search Invoices Gmail",
                "type": "n8n-nodes-base.gmail",
                "typeVersion": 2.1,
                "position": [220, 300],
                "parameters": {
                    "operation": "getAll",
                    "filters": {
                        "q": "subject:(fatura OR invoice OR recibo) has:attachment newer_than:1d",
                        "labelIds": [],
                    },
                    "returnAll": False,
                    "limit": 20,
                    "options": {"downloadAttachments": True},
                },
                "credentials": {"gmailOAuth2": {"id": "gmail-credential", "name": "Gmail OAuth2"}},
            },
            {
                "id": n_splitout,
                "name": "Split Emails",
                "type": "n8n-nodes-base.splitOut",
                "typeVersion": 1,
                "position": [460, 300],
                "parameters": {"fieldToSplitOut": "messages", "options": {}},
            },
            {
                "id": n_code,
                "name": "Extract Invoice Data",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [700, 300],
                "parameters": {
                    "jsCode": """
const email = $input.item.json;
const now = new Date();
const monthStr = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;

// Extrair remetente e assunto
const from = email.from || 'Desconhecido';
const subject = email.subject || 'Sem assunto';
const date = email.date || now.toISOString();
const emailId = email.id || '';

// Tentar extrair valor do assunto (ex: "Fatura €123.45")
const valueMatch = subject.match(/[€$]\\s?([\\d.,]+)/);
const extractedValue = valueMatch ? parseFloat(valueMatch[1].replace(',', '.')) : null;

return {
  json: {
    emailId,
    from,
    subject,
    date,
    monthStr,
    extractedValue,
    status: 'pendente',
    driveFolder: `Faturas/${monthStr}`,
    notionTitle: `${from.split('<')[0].trim()} — ${subject.substring(0, 50)}`
  }
};
""",
                },
            },
            {
                "id": n_notion,
                "name": "Create Notion Record",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [940, 300],
                "parameters": {
                    "method": "POST",
                    "url": "https://api.notion.com/v1/pages",
                    "authentication": "predefinedCredentialType",
                    "nodeCredentialType": "notionApi",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [{"name": "Notion-Version", "value": "2022-06-28"}]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"parent\": { \"database_id\": \"SUBSTITUIR_PELO_ID_DA_DATABASE_FATURAS\" },\n  \"properties\": {\n    \"Name\": { \"title\": [{ \"text\": { \"content\": \"{{ $json.notionTitle }}\" } }] },\n    \"Remetente\": { \"rich_text\": [{ \"text\": { \"content\": \"{{ $json.from }}\" } }] },\n    \"Data\": { \"date\": { \"start\": \"{{ $json.date }}\" } },\n    \"Valor\": { \"number\": {{ $json.extractedValue ?? 0 }} },\n    \"Status\": { \"select\": { \"name\": \"Pendente\" } },\n    \"Mês\": { \"rich_text\": [{ \"text\": { \"content\": \"{{ $json.monthStr }}\" } }] },\n    \"Email ID\": { \"rich_text\": [{ \"text\": { \"content\": \"{{ $json.emailId }}\" } }] }\n  }\n}",
                    "options": {},
                },
            },
        ],
        "connections": {
            "Daily 08:00":          {"main": [[{"node": "Search Invoices Gmail", "type": "main", "index": 0}]]},
            "Search Invoices Gmail": {"main": [[{"node": "Split Emails",          "type": "main", "index": 0}]]},
            "Split Emails":          {"main": [[{"node": "Extract Invoice Data",   "type": "main", "index": 0}]]},
            "Extract Invoice Data":  {"main": [[{"node": "Create Notion Record",   "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


# ─────────────────────────────────────────────────────────────────────────────
# TB-2: Daily PnL Report (diário às 18:00)
# Binance API → calcular PnL → Notion journal → Gmail summary
# ─────────────────────────────────────────────────────────────────────────────
def workflow_tb2_daily_pnl():
    n_schedule  = uid()
    n_account   = uid()
    n_trades    = uid()
    n_code      = uid()
    n_notion    = uid()
    n_gmail     = uid()

    return {
        "name": "[TB] Daily PnL Report — 18h",
        "nodes": [
            {
                "id": n_schedule,
                "name": "Daily 18:00",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 300],
                "parameters": {
                    "rule": {
                        "interval": [{"field": "cronExpression", "expression": "0 18 * * *"}]
                    }
                },
            },
            {
                "id": n_account,
                "name": "GET Account Balance",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [220, 200],
                "parameters": {
                    "method": "GET",
                    "url": "https://api.binance.com/api/v3/account",
                    "authentication": "predefinedCredentialType",
                    "nodeCredentialType": "httpHeaderAuth",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "X-MBX-APIKEY", "value": "={{ $vars.BINANCE_API_KEY }}"}
                        ]
                    },
                    "sendQuery": True,
                    "queryParameters": {
                        "parameters": [
                            {"name": "timestamp", "value": "={{ Date.now() }}"},
                            {"name": "signature", "value": "={{ /* HMAC-SHA256 */ '' }}"},
                        ]
                    },
                    "options": {},
                },
                "notes": "Requer BINANCE_API_KEY em Variables do n8n e assinatura HMAC. Ver README.",
            },
            {
                "id": n_trades,
                "name": "GET BTC Price (fallback)",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [220, 400],
                "parameters": {
                    "method": "GET",
                    "url": "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",
                    "options": {},
                },
            },
            {
                "id": n_code,
                "name": "Calculate PnL",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [460, 300],
                "parameters": {
                    "mode": "runOnceForAllItems",
                    "jsCode": """
// Nota: Binance account API requer autenticação HMAC-SHA256.
// Por enquanto este nó usa dados do ticker público como demonstração.
// Quando a autenticação estiver configurada, usar $('GET Account Balance').first().json

const ticker = $('GET BTC Price (fallback)').first().json;
const btcPrice = parseFloat(ticker.lastPrice || 0);
const priceChange24h = parseFloat(ticker.priceChangePercent || 0);
const high24h = parseFloat(ticker.highPrice || 0);
const low24h  = parseFloat(ticker.lowPrice || 0);
const volume  = parseFloat(ticker.volume || 0);

const now = new Date();
const dateStr = now.toISOString().split('T')[0];

const report = `📊 RELATÓRIO DIÁRIO — ${dateStr}
────────────────────────────
BTC/USDT
  Preço: $${btcPrice.toLocaleString('en-US', {maximumFractionDigits: 0})}
  Variação 24h: ${priceChange24h > 0 ? '+' : ''}${priceChange24h.toFixed(2)}%
  Máximo 24h: $${high24h.toLocaleString('en-US', {maximumFractionDigits: 0})}
  Mínimo 24h: $${low24h.toLocaleString('en-US', {maximumFractionDigits: 0})}
  Volume 24h: ${volume.toFixed(2)} BTC
────────────────────────────
⚙️ Para PnL completo: configurar Binance API Key em n8n Variables`;

return [{ json: { dateStr, btcPrice, priceChange24h, high24h, low24h, volume, report } }];
""",
                },
            },
            {
                "id": n_notion,
                "name": "Log to Notion Journal",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [700, 200],
                "parameters": {
                    "method": "POST",
                    "url": "https://api.notion.com/v1/pages",
                    "authentication": "predefinedCredentialType",
                    "nodeCredentialType": "notionApi",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [{"name": "Notion-Version", "value": "2022-06-28"}]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"parent\": { \"database_id\": \"SUBSTITUIR_PELO_ID_DATABASE_TRADING_JOURNAL\" },\n  \"properties\": {\n    \"Name\": { \"title\": [{ \"text\": { \"content\": \"Daily Report {{ $json.dateStr }}\" } }] },\n    \"BTC Price\": { \"number\": {{ $json.btcPrice }} },\n    \"Change 24h %\": { \"number\": {{ $json.priceChange24h }} },\n    \"Data\": { \"date\": { \"start\": \"{{ $json.dateStr }}\" } }\n  }\n}",
                    "options": {},
                },
            },
            {
                "id": n_gmail,
                "name": "Send Daily Summary",
                "type": "n8n-nodes-base.gmail",
                "typeVersion": 2.1,
                "position": [700, 400],
                "parameters": {
                    "operation": "send",
                    "sendTo": "pablomaciel2003.pm@gmail.com",
                    "subject": "=📊 Trading Report {{ $json.dateStr }} | BTC ${{ $json.btcPrice.toFixed(0) }}",
                    "emailType": "text",
                    "message": "={{ $json.report }}",
                    "options": {},
                },
                "credentials": {"gmailOAuth2": {"id": "gmail-credential", "name": "Gmail OAuth2"}},
            },
        ],
        "connections": {
            "Daily 18:00":                {"main": [[{"node": "GET Account Balance",       "type": "main", "index": 0},
                                                      {"node": "GET BTC Price (fallback)", "type": "main", "index": 0}]]},
            "GET Account Balance":         {"main": [[{"node": "Calculate PnL", "type": "main", "index": 0}]]},
            "GET BTC Price (fallback)":   {"main": [[{"node": "Calculate PnL", "type": "main", "index": 0}]]},
            "Calculate PnL":              {"main": [[{"node": "Log to Notion Journal", "type": "main", "index": 0},
                                                      {"node": "Send Daily Summary",   "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    workflows = [
        ("TB-1: Price Alert",    workflow_tb1_price_alert()),
        ("FAT-1: Invoice Scanner", workflow_fat1_invoice_scanner()),
        ("TB-2: Daily PnL Report", workflow_tb2_daily_pnl()),
    ]

    created = []
    for name, wf in workflows:
        try:
            result = create_workflow(wf)
            wf_id = result["id"]
            print(f"✅ {name} — criado (ID: {wf_id}) e ativado")
            created.append({"name": name, "id": wf_id})
        except Exception as e:
            print(f"❌ {name} — erro: {e}")

    print(f"\n{'─'*50}")
    print(f"✅ {len(created)}/{len(workflows)} workflows criados")
    print("\n⚠️  PRÓXIMOS PASSOS — Configurar credenciais em localhost:5678:")
    print("  1. Settings → Credentials → Add → Gmail OAuth2")
    print("  2. Settings → Credentials → Add → Notion API")
    print("  3. Substituir 'SUBSTITUIR_PELO_ID_DA_DATABASE_*' pelos IDs reais do Notion")
    print("  4. Para TB-2 completo: Settings → Variables → BINANCE_API_KEY")
