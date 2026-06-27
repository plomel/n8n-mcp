"""
WF-02 — Daily Morning Briefing às 09:00
Chama bot_state_api /briefing → formata mensagem Telegram com:
  - Estado do trading bot (posições + PnL + running)
  - Último vídeo gerado em viral-videos/output

Nota: Shopify orders BLOQUEADO — sem credencial Shopify no n8n.
Pré-requisito: python bot_state_api.py a correr (porta 8766)
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
BOT_API_BASE       = "http://host.docker.internal:8766"


def uid():
    return str(uuid.uuid4())


def create_workflow_api(workflow: dict) -> str:
    r = httpx.post(f"{N8N_URL}/api/v1/workflows", headers=HEADERS, json=workflow, timeout=30)
    r.raise_for_status()
    wf_id = r.json()["id"]
    r2 = httpx.post(f"{N8N_URL}/api/v1/workflows/{wf_id}/activate", headers=HEADERS, timeout=15)
    if r2.status_code not in (200, 201, 204):
        print(f"  ⚠️  activate retornou {r2.status_code}: {r2.text[:200]}")
    return wf_id


def delete_workflow(wf_id: str):
    r = httpx.delete(f"{N8N_URL}/api/v1/workflows/{wf_id}", headers=HEADERS, timeout=10)
    return r.status_code


def workflow_wf02():
    n_sched    = uid()
    n_wh       = uid()
    n_briefing = uid()
    n_code     = uid()
    n_tg       = uid()
    n_err      = uid()
    n_tg_err   = uid()

    return {
        "name": "[WF-02] Daily Morning Briefing (09:00)",
        "nodes": [
            {
                "id": n_sched,
                "name": "Daily 09:00",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 200],
                "parameters": {
                    "rule": {"interval": [{"field": "cronExpression", "expression": "0 9 * * *"}]}
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
                    "path": "wf-02-test",
                    "responseMode": "onReceived",
                    "options": {},
                },
            },
            {
                "id": n_briefing,
                "name": "GET Briefing",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [250, 300],
                "parameters": {
                    "method": "GET",
                    "url": f"{BOT_API_BASE}/briefing",
                    "options": {"timeout": 5000},
                },
            },
            {
                "id": n_code,
                "name": "Format Briefing",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [500, 300],
                "parameters": {
                    "mode": "runOnceForAllItems",
                    "jsCode": r"""
const d = $('GET Briefing').first().json;
const running  = d.bot_running === true;
const state    = d.positions || {};
const pnl      = d.pnl || {};
const today    = new Date().toLocaleDateString('pt-PT');
const lastVideo = d.last_video || 'Nenhum';

const lines = [`📊 <b>Briefing ${today}</b>`];

// --- Bot Trading ---
lines.push(`\n🤖 <b>Trading Bot</b> — ${running ? '✅ A correr' : '❌ Parado'}`);
const positions = Object.entries(state);
if (positions.length > 0) {
  for (const [sym, p] of positions) {
    lines.push(`  📈 ${p.side} ${sym}: entry=${p.entry} | SL=${p.sl} | TP=${p.tp}`);
    lines.push(`     Qty: ${p.quantity} | Leverage: ${p.leverage}×`);
  }
  if (pnl.pnl_usd !== undefined) {
    const sign = pnl.pnl_usd >= 0 ? '+' : '';
    lines.push(`  💰 PnL: ${sign}${Number(pnl.pnl_usd).toFixed(3)} USD`);
    if (pnl.starting_balance) lines.push(`  💵 Saldo: ${Number(pnl.starting_balance).toFixed(2)} USD`);
  }
} else {
  lines.push('  Sem posições abertas');
}

// --- Último vídeo ---
lines.push(`\n🎬 <b>Último vídeo</b>`);
lines.push(`  ${lastVideo !== 'Nenhum' ? lastVideo : 'Nenhum gerado ainda'}`);

// --- Shopify (bloqueado) ---
lines.push(`\n🛍️ <b>WorkGadget</b> — ⚠️ Shopify não ligado`);

return [{ json: { text: lines.join('\n') } }];
""",
                },
            },
            {
                "id": n_tg,
                "name": "Telegram Briefing",
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
                    "text": "=❌ <b>WF-02 Erro</b>\n{{ $json.execution?.error?.message || 'Erro desconhecido' }}",
                    "additionalFields": {"parse_mode": "HTML"},
                },
                "credentials": {
                    "telegramApi": {"id": TELEGRAM_CRED_ID, "name": TELEGRAM_CRED_NAME}
                },
            },
        ],
        "connections": {
            "Daily 09:00":  {"main": [[{"node": "GET Briefing", "type": "main", "index": 0}]]},
            "Webhook Test": {"main": [[{"node": "GET Briefing", "type": "main", "index": 0}]]},
            "GET Briefing":    {"main": [[{"node": "Format Briefing", "type": "main", "index": 0}]]},
            "Format Briefing": {"main": [[{"node": "Telegram Briefing", "type": "main", "index": 0}]]},
            "Error Trigger":   {"main": [[{"node": "Telegram Error", "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


if __name__ == "__main__":
    # Apagar versão anterior se existir
    OLD_IDS = []  # preencher se re-criar
    for old_id in OLD_IDS:
        s = delete_workflow(old_id)
        print(f"Apagado {old_id}: HTTP {s}")

    try:
        wf_id = create_workflow_api(workflow_wf02())
        r = httpx.get(f"{N8N_URL}/api/v1/workflows/{wf_id}", headers=HEADERS, timeout=10)
        active = r.json().get("active", False) if r.status_code == 200 else "?"
        print(f"{'✅' if active else '⚠️ '} WF-02 Morning Briefing — ID={wf_id} active={active}")
        print(f"Webhook de teste: POST http://localhost:5678/webhook/wf-02-test")
    except Exception as e:
        print(f"❌ WF-02 — {e}")
