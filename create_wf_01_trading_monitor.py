"""
WF-01: Trading Bot Monitor + Daily Summary
  WF-01a — Health check a cada 30 min: lê .bot_state.json + verifica processo → alerta se bot OFF com posição aberta
  WF-01b — Daily summary às 17:30: estado + PnL → Telegram sempre

Nota: n8n corre em Docker. Execute Command corre no Linux container.
Paths Windows só funcionam se o docker-compose montar o host filesystem.
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

BOT_STATE_PATH = r"C:\Desenvolvimento\trading-bot\.bot_state.json"
DAILY_PNL_PATH = r"C:\Desenvolvimento\trading-bot\.daily_pnl.json"
LOG_PATH       = r"C:\n8n-logs\wf-01.log"


def uid():
    return str(uuid.uuid4())


def create_workflow(workflow: dict) -> dict:
    r = httpx.post(f"{N8N_URL}/api/v1/workflows", headers=HEADERS, json=workflow, timeout=30)
    r.raise_for_status()
    data = r.json()
    wf_id = data["id"]
    httpx.patch(f"{N8N_URL}/api/v1/workflows/{wf_id}/activate", headers=HEADERS, timeout=30)
    return data


def workflow_wf01a_health_check():
    """A cada 30 min: verifica se o bot está a correr. Alerta se bot OFF com posição aberta."""
    n_sched   = uid()
    n_state   = uid()
    n_proc    = uid()
    n_code    = uid()
    n_if      = uid()
    n_tg_ok   = uid()
    n_err     = uid()
    n_tg_err  = uid()

    return {
        "name": "[WF-01a] Trading Bot — Health Check (30 min)",
        "nodes": [
            {
                "id": n_sched,
                "name": "Every 30 min",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 300],
                "parameters": {
                    "rule": {"interval": [{"field": "minutes", "minutesInterval": 30}]}
                },
            },
            {
                "id": n_state,
                "name": "Read Bot State",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [220, 200],
                "parameters": {
                    "command": (
                        f"powershell.exe -NonInteractive -Command "
                        f"\"Get-Content '{BOT_STATE_PATH}' -Raw 2>&1 | "
                        f"Tee-Object -Append '{LOG_PATH}'\""
                    )
                },
            },
            {
                "id": n_proc,
                "name": "Check Python Process",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [220, 400],
                "parameters": {
                    "command": (
                        "powershell.exe -NonInteractive -Command "
                        "\"(tasklist /FI 'IMAGENAME eq python.exe' /NH) -ne 'INFO: No tasks are running which match the specified criteria.'\""
                    )
                },
            },
            {
                "id": n_code,
                "name": "Parse + Format Alert",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [460, 300],
                "parameters": {
                    "mode": "runOnceForAllItems",
                    "jsCode": r"""
const stateRaw  = $('Read Bot State').first().json.stdout  || '{}';
const procOut   = $('Check Python Process').first().json.stdout || '';

let state = {};
try { state = JSON.parse(stateRaw.trim()); } catch(e) { state = {}; }

const botRunning  = procOut.trim() === 'True';
const positions   = Object.keys(state);
const hasPosition = positions.length > 0;
const now = new Date().toISOString().slice(0,16).replace('T',' ');

let posLines = '';
for (const sym of positions) {
  const p = state[sym];
  posLines += `\n  📈 ${p.side} ${sym}: entry=${p.entry} | SL=${p.sl} | TP=${p.tp} | qty=${p.quantity}`;
}

// Só envia alerta se bot OFF com posição aberta
const shouldAlert = !botRunning && hasPosition;

const alertMsg = shouldAlert
  ? `🚨 <b>BOT PARADO COM POSIÇÃO ABERTA!</b> — ${now}${posLines}\n\n⚠️ SL em ${state[positions[0]]?.sl} sem monitorização!`
  : null;

return [{ json: { botRunning, hasPosition, positions, shouldAlert, alertMsg, now } }];
""",
                },
            },
            {
                "id": n_if,
                "name": "Should Alert?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "position": [700, 300],
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
                "position": [940, 200],
                "parameters": {
                    "chatId": TELEGRAM_CHAT_ID,
                    "text": "={{ $json.alertMsg }}",
                    "additionalFields": {"parse_mode": "HTML"},
                },
                "credentials": {
                    "telegramApi": {"id": TELEGRAM_CRED_ID, "name": TELEGRAM_CRED_NAME}
                },
            },
            # Error Trigger → Telegram
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
                "position": [220, 600],
                "parameters": {
                    "chatId": TELEGRAM_CHAT_ID,
                    "text": "=❌ <b>WF-01a Erro</b>\nNó: {{ $json.execution.lastNodeExecuted }}\nErro: {{ $json.execution.error.message }}",
                    "additionalFields": {"parse_mode": "HTML"},
                },
                "credentials": {
                    "telegramApi": {"id": TELEGRAM_CRED_ID, "name": TELEGRAM_CRED_NAME}
                },
            },
        ],
        "connections": {
            "Every 30 min": {
                "main": [[
                    {"node": "Read Bot State",      "type": "main", "index": 0},
                    {"node": "Check Python Process","type": "main", "index": 0},
                ]]
            },
            "Read Bot State":       {"main": [[{"node": "Parse + Format Alert", "type": "main", "index": 0}]]},
            "Check Python Process": {"main": [[{"node": "Parse + Format Alert", "type": "main", "index": 0}]]},
            "Parse + Format Alert": {"main": [[{"node": "Should Alert?",        "type": "main", "index": 0}]]},
            "Should Alert?": {
                "main": [
                    [{"node": "Telegram Alert", "type": "main", "index": 0}],  # true
                    []  # false — não faz nada
                ]
            },
            "Error Trigger": {"main": [[{"node": "Telegram Error", "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


def workflow_wf01b_daily_summary():
    """Às 17:30 UTC: envia sempre o resumo do estado + PnL do dia."""
    n_sched  = uid()
    n_state  = uid()
    n_pnl    = uid()
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
                "position": [0, 300],
                "parameters": {
                    "rule": {"interval": [{"field": "cronExpression", "expression": "30 17 * * *"}]}
                },
            },
            {
                "id": n_state,
                "name": "Read Bot State",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [220, 200],
                "parameters": {
                    "command": f"powershell.exe -NonInteractive -Command \"Get-Content '{BOT_STATE_PATH}' -Raw 2>&1\""
                },
            },
            {
                "id": n_pnl,
                "name": "Read Daily PnL",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [220, 400],
                "parameters": {
                    "command": f"powershell.exe -NonInteractive -Command \"Get-Content '{DAILY_PNL_PATH}' -Raw 2>&1\""
                },
            },
            {
                "id": n_code,
                "name": "Format Summary",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [460, 300],
                "parameters": {
                    "mode": "runOnceForAllItems",
                    "jsCode": r"""
const stateRaw = $('Read Bot State').first().json.stdout || '{}';
const pnlRaw   = $('Read Daily PnL').first().json.stdout || '{}';

let state = {};
let pnl   = {};
try { state = JSON.parse(stateRaw.trim()); } catch(e) {}
try { pnl   = JSON.parse(pnlRaw.trim());   } catch(e) {}

const now = new Date().toISOString().slice(0,10);
const positions = Object.entries(state);

let lines = [`📊 <b>Trading Bot — ${now}</b>`];

if (positions.length > 0) {
  for (const [sym, p] of positions) {
    lines.push(`📈 ${p.side} ${sym}`);
    lines.push(`   Entry: ${p.entry} | SL: ${p.sl} | TP: ${p.tp}`);
    lines.push(`   Qty: ${p.quantity} | Leverage: ${p.leverage}×`);
    const openedDate = p.opened ? p.opened.slice(0,10) : '?';
    lines.push(`   Aberta: ${openedDate}`);
  }
} else {
  lines.push('🤖 Sem posições abertas');
}

if (pnl.pnl_usd !== undefined) {
  const sign = pnl.pnl_usd >= 0 ? '+' : '';
  lines.push(`💰 PnL hoje: ${sign}${pnl.pnl_usd.toFixed(3)} USD`);
  if (pnl.starting_balance) lines.push(`💵 Saldo inicial: ${pnl.starting_balance.toFixed(2)} USD`);
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
                "position": [700, 300],
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
                "position": [220, 600],
                "parameters": {
                    "chatId": TELEGRAM_CHAT_ID,
                    "text": "=❌ <b>WF-01b Erro</b>\nNó: {{ $json.execution.lastNodeExecuted }}\nErro: {{ $json.execution.error.message }}",
                    "additionalFields": {"parse_mode": "HTML"},
                },
                "credentials": {
                    "telegramApi": {"id": TELEGRAM_CRED_ID, "name": TELEGRAM_CRED_NAME}
                },
            },
        ],
        "connections": {
            "Daily 17:30": {
                "main": [[
                    {"node": "Read Bot State", "type": "main", "index": 0},
                    {"node": "Read Daily PnL", "type": "main", "index": 0},
                ]]
            },
            "Read Bot State": {"main": [[{"node": "Format Summary", "type": "main", "index": 0}]]},
            "Read Daily PnL": {"main": [[{"node": "Format Summary", "type": "main", "index": 0}]]},
            "Format Summary": {"main": [[{"node": "Telegram Summary", "type": "main", "index": 0}]]},
            "Error Trigger": {"main": [[{"node": "Telegram Error", "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


if __name__ == "__main__":
    workflows = [
        ("WF-01a Health Check",  workflow_wf01a_health_check()),
        ("WF-01b Daily Summary", workflow_wf01b_daily_summary()),
    ]
    created = []
    for name, wf in workflows:
        try:
            result = create_workflow(wf)
            print(f"✅ {name} criado e activado — ID: {result['id']}")
            created.append(result['id'])
        except Exception as e:
            print(f"❌ {name} falhou: {e}")

    print(f"\n{len(created)}/2 workflows criados")
    if created:
        print("\nIDs para teste manual:")
        for wf_id in created:
            print(f"  POST http://localhost:5678/api/v1/workflows/{wf_id}/run")
