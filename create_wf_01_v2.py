"""
WF-01 v2 — Trading Bot Monitor + Daily Summary (sem executeCommand)
Usa HTTP Request → bot_state_api.py em http://host.docker.internal:8766

Pré-requisito: python bot_state_api.py a correr (porta 8766)
  Pablo precisa de iniciar: python C:\Desenvolvimento\trading-bot\bot_state_api.py
"""
import httpx
import uuid
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
API_KEY = os.getenv("N8N_API_KEY", "")
HEADERS = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}

TELEGRAM_CRED_ID   = "e7EYx0WgsI6TiI7x"
TELEGRAM_CRED_NAME = "Telegram Bot (Bots)"
TELEGRAM_CHAT_ID   = "1206208489"

# n8n Docker acede ao host via host.docker.internal
BOT_API_BASE = "http://host.docker.internal:8766"


def uid():
    return str(uuid.uuid4())


def create_workflow_api(workflow: dict) -> str:
    """Cria o workflow e activa via POST /activate."""
    r = httpx.post(f"{N8N_URL}/api/v1/workflows", headers=HEADERS, json=workflow, timeout=30)
    r.raise_for_status()
    wf_id = r.json()["id"]
    # Activar via POST (correcto em n8n v2)
    r2 = httpx.post(f"{N8N_URL}/api/v1/workflows/{wf_id}/activate", headers=HEADERS, timeout=15)
    if r2.status_code not in (200, 201, 204):
        print(f"  ⚠️  activate retornou {r2.status_code}: {r2.text[:200]}")
    return wf_id


def delete_workflow(wf_id: str):
    r = httpx.delete(f"{N8N_URL}/api/v1/workflows/{wf_id}", headers=HEADERS, timeout=10)
    return r.status_code


# ─── WF-01a: Health Check a cada 30 min ─────────────────────────────────────

def workflow_wf01a():
    n_sched  = uid()
    n_wh     = uid()  # webhook para teste
    n_status = uid()
    n_code   = uid()
    n_if     = uid()
    n_tg_ok  = uid()
    n_err    = uid()
    n_tg_err = uid()

    return {
        "name": "[WF-01a] Trading Bot — Health Check (30 min)",
        "nodes": [
            {
                "id": n_sched,
                "name": "Every 30 min",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 200],
                "parameters": {
                    "rule": {"interval": [{"field": "minutes", "minutesInterval": 30}]}
                },
            },
            {
                "id": n_wh,
                "name": "Webhook Test",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [0, 400],
                "webhookId": uid(),
                "parameters": {
                    "httpMethod": "POST",
                    "path": "wf-01a-test",
                    "responseMode": "onReceived",
                    "options": {},
                },
            },
            {
                "id": n_status,
                "name": "GET Bot Status",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [250, 300],
                "parameters": {
                    "method": "GET",
                    "url": f"{BOT_API_BASE}/status",
                    "options": {"timeout": 5000},
                },
            },
            {
                "id": n_code,
                "name": "Check Alert Condition",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [500, 300],
                "parameters": {
                    "mode": "runOnceForAllItems",
                    "jsCode": r"""
const d = $('GET Bot Status').first().json;
const botRunning  = d.bot_running === true;
const hasPosition = d.has_open_positions === true;
const now = new Date().toISOString().slice(0,16).replace('T',' ');

// Só alerta se bot OFF com posição aberta
const shouldAlert = !botRunning && hasPosition;

let alertMsg = '';
if (shouldAlert) {
  const positions = d.positions || {};
  const posLines = Object.entries(positions)
    .map(([sym, p]) => `  📈 ${p.side} ${sym}: entry=${p.entry} | SL=${p.sl} | TP=${p.tp}`)
    .join('\n');
  alertMsg = `🚨 <b>BOT PARADO COM POSIÇÃO ABERTA!</b> — ${now}\n${posLines}\n\n⚠️ SL em risco sem monitorização!`;
}

return [{ json: { botRunning, hasPosition, shouldAlert, alertMsg, positions: d.positions } }];
""",
                },
            },
            {
                "id": n_if,
                "name": "Should Alert?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "position": [750, 300],
                "parameters": {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                        "conditions": [
                            {
                                "leftValue": "={{ $json.shouldAlert }}",
                                "rightValue": True,
                                "operator": {"type": "boolean", "operation": "equals"},
                            }
                        ],
                        "combinator": "and",
                    }
                },
            },
            {
                "id": n_tg_ok,
                "name": "Telegram Alert",
                "type": "n8n-nodes-base.telegram",
                "typeVersion": 1.2,
                "position": [1000, 200],
                "parameters": {
                    "chatId": TELEGRAM_CHAT_ID,
                    "text": "={{ $json.alertMsg }}",
                    "additionalFields": {"parse_mode": "HTML"},
                },
                "credentials": {
                    "telegramApi": {"id": TELEGRAM_CRED_ID, "name": TELEGRAM_CRED_NAME}
                },
            },
            {
                "id": n_err,
                "name": "Error Trigger",
                "type": "n8n-nodes-base.errorTrigger",
                "typeVersion": 1,
                "position": [0, 600],
                "parameters": {},
            },
            {
                "id": n_tg_err,
                "name": "Telegram Error",
                "type": "n8n-nodes-base.telegram",
                "typeVersion": 1.2,
                "position": [250, 600],
                "parameters": {
                    "chatId": TELEGRAM_CHAT_ID,
                    "text": "=❌ <b>WF-01a Erro</b>\n{{ $json.execution?.error?.message || $json.error?.message || 'Erro desconhecido' }}",
                    "additionalFields": {"parse_mode": "HTML"},
                },
                "credentials": {
                    "telegramApi": {"id": TELEGRAM_CRED_ID, "name": TELEGRAM_CRED_NAME}
                },
            },
        ],
        "connections": {
            "Every 30 min":  {"main": [[{"node": "GET Bot Status", "type": "main", "index": 0}]]},
            "Webhook Test":  {"main": [[{"node": "GET Bot Status", "type": "main", "index": 0}]]},
            "GET Bot Status": {"main": [[{"node": "Check Alert Condition", "type": "main", "index": 0}]]},
            "Check Alert Condition": {"main": [[{"node": "Should Alert?", "type": "main", "index": 0}]]},
            "Should Alert?": {
                "main": [
                    [{"node": "Telegram Alert", "type": "main", "index": 0}],
                    []
                ]
            },
            "Error Trigger": {"main": [[{"node": "Telegram Error", "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


# ─── WF-01b: Daily Summary às 17:30 ─────────────────────────────────────────

def workflow_wf01b():
    n_sched  = uid()
    n_wh     = uid()
    n_status = uid()
    n_code   = uid()
    n_tg     = uid()
    n_err    = uid()
    n_tg_err = uid()

    return {
        "name": "[WF-01b] Trading Bot — Daily Summary (17:30)",
        "nodes": [
            {
                "id": n_sched,
                "name": "Daily 17:30",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 200],
                "parameters": {
                    "rule": {"interval": [{"field": "cronExpression", "expression": "30 17 * * *"}]}
                },
            },
            {
                "id": n_wh,
                "name": "Webhook Test",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [0, 400],
                "webhookId": uid(),
                "parameters": {
                    "httpMethod": "POST",
                    "path": "wf-01b-test",
                    "responseMode": "onReceived",
                    "options": {},
                },
            },
            {
                "id": n_status,
                "name": "GET Bot Status",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [250, 300],
                "parameters": {
                    "method": "GET",
                    "url": f"{BOT_API_BASE}/status",
                    "options": {"timeout": 5000},
                },
            },
            {
                "id": n_code,
                "name": "Format Summary",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [500, 300],
                "parameters": {
                    "mode": "runOnceForAllItems",
                    "jsCode": r"""
const d = $('GET Bot Status').first().json;
const state    = d.positions || {};
const pnl      = d.pnl || {};
const running  = d.bot_running === true;
const now      = new Date().toISOString().slice(0,10);

let lines = [`📊 <b>Trading Bot — ${now}</b>`];
lines.push(`🤖 Status: ${running ? '✅ A correr' : '❌ Parado'}`);

const positions = Object.entries(state);
if (positions.length > 0) {
  for (const [sym, p] of positions) {
    lines.push(`📈 ${p.side} ${sym}`);
    lines.push(`   Entry: ${p.entry} | SL: ${p.sl} | TP: ${p.tp}`);
    lines.push(`   Qty: ${p.quantity} | Leverage: ${p.leverage}×`);
    if (p.opened) lines.push(`   Aberta: ${p.opened.slice(0,10)}`);
  }
} else {
  lines.push('  Sem posições abertas');
}

if (pnl.pnl_usd !== undefined) {
  const sign = pnl.pnl_usd >= 0 ? '+' : '';
  lines.push(`💰 PnL: ${sign}${Number(pnl.pnl_usd).toFixed(3)} USD`);
  if (pnl.starting_balance) lines.push(`💵 Saldo: ${Number(pnl.starting_balance).toFixed(2)} USD`);
}

return [{ json: { text: lines.join('\n') } }];
""",
                },
            },
            {
                "id": n_tg,
                "name": "Telegram Summary",
                "type": "n8n-nodes-base.telegram",
                "typeVersion": 1.2,
                "position": [750, 300],
                "parameters": {
                    "chatId": TELEGRAM_CHAT_ID,
                    "text": "={{ $json.text }}",
                    "additionalFields": {"parse_mode": "HTML"},
                },
                "credentials": {
                    "telegramApi": {"id": TELEGRAM_CRED_ID, "name": TELEGRAM_CRED_NAME}
                },
            },
            {
                "id": n_err,
                "name": "Error Trigger",
                "type": "n8n-nodes-base.errorTrigger",
                "typeVersion": 1,
                "position": [0, 600],
                "parameters": {},
            },
            {
                "id": n_tg_err,
                "name": "Telegram Error",
                "type": "n8n-nodes-base.telegram",
                "typeVersion": 1.2,
                "position": [250, 600],
                "parameters": {
                    "chatId": TELEGRAM_CHAT_ID,
                    "text": "=❌ <b>WF-01b Erro</b>\n{{ $json.execution?.error?.message || 'Erro desconhecido' }}",
                    "additionalFields": {"parse_mode": "HTML"},
                },
                "credentials": {
                    "telegramApi": {"id": TELEGRAM_CRED_ID, "name": TELEGRAM_CRED_NAME}
                },
            },
        ],
        "connections": {
            "Daily 17:30":   {"main": [[{"node": "GET Bot Status", "type": "main", "index": 0}]]},
            "Webhook Test":  {"main": [[{"node": "GET Bot Status", "type": "main", "index": 0}]]},
            "GET Bot Status": {"main": [[{"node": "Format Summary", "type": "main", "index": 0}]]},
            "Format Summary": {"main": [[{"node": "Telegram Summary", "type": "main", "index": 0}]]},
            "Error Trigger":  {"main": [[{"node": "Telegram Error",  "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


if __name__ == "__main__":
    # Apagar versões anteriores quebradas
    OLD_IDS = ["xWpLe3Aj1q94nvLM", "xC2OqCUZ6frU7Zex"]
    for old_id in OLD_IDS:
        s = delete_workflow(old_id)
        print(f"Apagado {old_id}: HTTP {s}")

    # Criar novas versões
    workflows = [
        ("WF-01a Health Check",  workflow_wf01a()),
        ("WF-01b Daily Summary", workflow_wf01b()),
    ]

    created_ids = []
    for name, wf in workflows:
        try:
            wf_id = create_workflow_api(wf)
            # Verificar activação
            r = httpx.get(f"{N8N_URL}/api/v1/workflows/{wf_id}", headers=HEADERS, timeout=10)
            active = r.json().get("active", False) if r.status_code == 200 else "?"
            print(f"{'✅' if active else '⚠️ '} {name} — ID={wf_id} active={active}")
            created_ids.append((name, wf_id, active))
        except Exception as e:
            print(f"❌ {name} — {e}")

    print(f"\nWebhooks de teste (com bot_state_api a correr):")
    for name, wf_id, _ in created_ids:
        suffix = "wf-01a-test" if "01a" in name else "wf-01b-test"
        print(f"  {name}: POST http://localhost:5678/webhook/{suffix}")
