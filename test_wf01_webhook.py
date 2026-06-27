"""
Adiciona webhook trigger ao WF-01b para teste manual e depois aciona.
Testa se o Execute Command consegue ler ficheiros Windows dentro do Docker n8n.
"""
import httpx
import uuid
import os
import json
import time
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

WEBHOOK_PATH = "wf-01b-test"


def uid():
    return str(uuid.uuid4())


def create_wf01b_with_webhook():
    """Recria WF-01b com webhook trigger para teste."""
    n_webhook = uid()
    n_state   = uid()
    n_pnl     = uid()
    n_code    = uid()
    n_tg      = uid()
    n_err     = uid()
    n_tg_err  = uid()

    return {
        "name": "[WF-01b] Trading Bot — Daily Summary (Webhook+17:30)",
        "nodes": [
            # Webhook para teste manual
            {
                "id": n_webhook,
                "name": "Webhook Test",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [0, 100],
                "parameters": {
                    "httpMethod": "POST",
                    "path": WEBHOOK_PATH,
                    "responseMode": "onReceived",
                    "responseData": "firstEntryJson",
                    "options": {},
                },
                "webhookId": uid(),
            },
            # Schedule para produção
            {
                "id": uid(),
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
const pnlRaw   = $('Read Daily PnL').first().json.stdout  || '{}';

let state = {}, pnl = {};
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
  lines.push(`💰 PnL hoje: ${sign}${Number(pnl.pnl_usd).toFixed(3)} USD`);
  if (pnl.starting_balance) lines.push(`💵 Saldo inicial: ${Number(pnl.starting_balance).toFixed(2)} USD`);
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
            "Webhook Test": {
                "main": [[
                    {"node": "Read Bot State", "type": "main", "index": 0},
                    {"node": "Read Daily PnL", "type": "main", "index": 0},
                ]]
            },
            "Daily 17:30": {
                "main": [[
                    {"node": "Read Bot State", "type": "main", "index": 0},
                    {"node": "Read Daily PnL", "type": "main", "index": 0},
                ]]
            },
            "Read Bot State": {"main": [[{"node": "Format Summary", "type": "main", "index": 0}]]},
            "Read Daily PnL": {"main": [[{"node": "Format Summary", "type": "main", "index": 0}]]},
            "Format Summary": {"main": [[{"node": "Telegram Summary", "type": "main", "index": 0}]]},
            "Error Trigger":  {"main": [[{"node": "Telegram Error",   "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


def delete_workflow(wf_id: str):
    r = httpx.delete(f"{N8N_URL}/api/v1/workflows/{wf_id}", headers=HEADERS, timeout=15)
    return r.status_code


def create_and_activate(wf: dict) -> str:
    r = httpx.post(f"{N8N_URL}/api/v1/workflows", headers=HEADERS, json=wf, timeout=30)
    r.raise_for_status()
    wf_id = r.json()["id"]
    httpx.patch(f"{N8N_URL}/api/v1/workflows/{wf_id}/activate", headers=HEADERS, timeout=15)
    return wf_id


def get_latest_execution(wf_id: str) -> dict:
    r = httpx.get(f"{N8N_URL}/api/v1/executions?workflowId={wf_id}&limit=1", headers=HEADERS, timeout=15)
    data = r.json().get("data", [])
    return data[0] if data else {}


if __name__ == "__main__":
    # 1. Apagar WF-01b antigo
    old_id = "6aw2BKtD94UPQyxx"
    status = delete_workflow(old_id)
    print(f"Apagado WF-01b antigo ({old_id}): {status}")

    # 2. Criar novo com webhook
    wf_id = create_and_activate(create_wf01b_with_webhook())
    print(f"WF-01b recriado: ID={wf_id}")
    print(f"Webhook URL (produção): http://localhost:5678/webhook/{WEBHOOK_PATH}")

    # 3. Acionar via webhook (produção mode, workflow activo)
    time.sleep(2)
    print(f"\nAcionando via webhook...")
    try:
        resp = httpx.post(
            f"{N8N_URL}/webhook/{WEBHOOK_PATH}",
            json={"source": "test"},
            timeout=30,
        )
        print(f"Webhook response: {resp.status_code} — {resp.text[:300]}")
    except Exception as e:
        print(f"Webhook erro: {e}")

    # 4. Aguardar execução + verificar resultado
    time.sleep(5)
    print("\nVerificando execução mais recente...")
    exec_data = get_latest_execution(wf_id)
    if exec_data:
        print(f"  ID: {exec_data.get('id')}")
        print(f"  Status: {exec_data.get('status')}")
        print(f"  Finished: {exec_data.get('finished')}")
        print(f"  StartedAt: {exec_data.get('startedAt')}")
    else:
        print("  Nenhuma execução encontrada")

    # Verificar detalhes da execução se existir
    exec_id = exec_data.get("id")
    if exec_id:
        r2 = httpx.get(f"{N8N_URL}/api/v1/executions/{exec_id}", headers=HEADERS, timeout=15)
        full = r2.json()
        run_data = full.get("data", {}).get("resultData", {}).get("runData", {})
        print("\nDetalhes por nó:")
        for node_name, node_runs in run_data.items():
            if node_runs:
                last_run = node_runs[-1]
                err = last_run.get("error")
                output = last_run.get("data", {}).get("main", [[]])[0]
                if err:
                    print(f"  ❌ {node_name}: {err.get('message','?')}")
                elif output:
                    # Mostrar stdout se for Execute Command
                    first_item = output[0].get("json", {}) if output else {}
                    stdout = first_item.get("stdout", "")
                    if stdout:
                        print(f"  ✅ {node_name}: stdout={stdout[:100]!r}")
                    else:
                        print(f"  ✅ {node_name}: OK")
                else:
                    print(f"  ⚪ {node_name}: sem output")

    print(f"\nWF-01b novo ID: {wf_id} (actualizar referências)")
