"""
WF-04 — WG-5 Content Scheduler (v2 — fixes aplicados)

Fixes:
- Dois scheduleTrigger nodes separados (Terça + Sexta) em vez de array incerto
- HTTP Request body para WF-03 como dict com campos explícitos (não string JSON)
- Shopify 401 tratado graciosamente — Code node usa fallback
- Error Trigger usa expressão pura ={{ }}
- OLD_IDS detectados dinamicamente

Pipeline:
  [Schedule Terça 09:00] ──→ [GET Shopify]
  [Schedule Sexta 09:00] ──→ [GET Shopify]
  [Webhook Test] ──────────→ [Seleccionar Produto]
  [GET Shopify] ───────────→ [Seleccionar Produto]
  [Seleccionar Produto] ───→ [Notificar WF-03] → [Telegram]
  [Error Trigger] ─────────→ [Telegram Erro]
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
SHOPIFY_STORE      = "cy7rcx-k6.myshopify.com"


def uid():
    return str(uuid.uuid4())


def get_wf_id_by_name(fragment: str) -> str | None:
    r = httpx.get(f"{N8N_URL}/api/v1/workflows?limit=50", headers=HEADERS, timeout=10)
    for wf in r.json().get("data", []):
        if fragment in wf.get("name", ""):
            return wf["id"]
    return None


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


def workflow_wf04():
    # FIX: dois scheduleTrigger separados em vez de array de cronExpressions
    n_sched_tue = uid()
    n_sched_fri = uid()
    n_wh        = uid()
    n_shopify   = uid()
    n_select    = uid()
    n_notify    = uid()
    n_tg        = uid()
    n_err       = uid()
    n_tg_err    = uid()

    return {
        "name": "[WF-04] WG-5 Content Scheduler (Terça+Sexta)",
        "nodes": [
            {
                "id": n_sched_tue,
                "name": "Schedule Terça 09:00",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 100],
                "parameters": {
                    "rule": {"interval": [{"field": "cronExpression", "expression": "0 9 * * 2"}]}
                },
            },
            {
                "id": n_sched_fri,
                "name": "Schedule Sexta 09:00",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 250],
                "parameters": {
                    "rule": {"interval": [{"field": "cronExpression", "expression": "0 9 * * 5"}]}
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
                    "path": "wf-04-test",
                    "responseMode": "onReceived",
                    "options": {},
                },
            },
            {
                "id": n_shopify,
                "name": "GET Shopify Produtos",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [250, 175],
                "parameters": {
                    "method": "GET",
                    "url": f"https://{SHOPIFY_STORE}/admin/api/2024-01/products.json?limit=10&status=active",
                    "options": {
                        "timeout": 10000,
                        "response": {"response": {"neverError": True}},
                    },
                    "headers": {
                        "parameters": [
                            {
                                "name": "X-Shopify-Access-Token",
                                "value": "SHOPIFY_TOKEN_PENDENTE",
                            }
                        ]
                    },
                },
            },
            {
                "id": n_select,
                "name": "Seleccionar Produto + Formatar Plano",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [500, 300],
                "parameters": {
                    "mode": "runOnceForAllItems",
                    "jsCode": r"""
let productTitle = 'Produto Teste';
let productPrice = '0.00';
let productDesc  = 'Descrição de teste';

// Prioridade 1: webhook test com product_info
try {
  const webhookBody = $('Webhook Test').first()?.json?.body || {};
  if (webhookBody.product_info) {
    const parts = webhookBody.product_info.split('|');
    productTitle = parts[0] || productTitle;
    productPrice = parts[1] || productPrice;
    productDesc  = parts[2] || productDesc;
  }
} catch {}

// Prioridade 2: dados Shopify (se token configurado e request bem-sucedido)
if (productTitle === 'Produto Teste') {
  try {
    const shopifyData = $('GET Shopify Produtos').first()?.json;
    const products = shopifyData?.products || [];
    if (products.length > 0) {
      const idx = new Date().getDay() % products.length;
      const p = products[idx];
      productTitle = p.title || productTitle;
      productPrice = String(p.variants?.[0]?.price || productPrice);
      productDesc  = (p.body_html || '').replace(/<[^>]+>/g, '').slice(0, 100);
    }
  } catch {}
}

const today = new Date().toISOString().slice(0, 10);
const text = [
  `📋 <b>WF-04 Plano de Conteúdo — ${today}</b>`,
  ``,
  `🛍️ Produto: <b>${productTitle}</b>`,
  `💶 Preço: ${productPrice} USD`,
  `📝 ${productDesc.slice(0, 80)}`,
  ``,
  `⏳ Pipeline pendente:`,
  `  1. build_story_video.py (script + voz + render)`,
  `  2. youtube_upload.py (configurar YOUTUBE_REFRESH_TOKEN)`,
].join('\n');

return [{ json: { text, productTitle, productPrice, productDesc, today } }];
""",
                },
            },
            {
                "id": n_notify,
                "name": "Notificar WF-03",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [750, 300],
                "parameters": {
                    "method": "POST",
                    "url": "http://localhost:5678/webhook/yt2viral-ready",
                    "sendBody": True,
                    "bodyParameters": {
                        "parameters": [
                            {"name": "videoId",  "value": "wf04-placeholder"},
                            {"name": "mp4Path",  "value": "PENDENTE — build_story_video.py"},
                            {"name": "title",    "value": "={{ $json.productTitle }}"},
                            {"name": "durationS","value": "0"},
                            {"name": "reason",   "value": "WF-04 Content Scheduler"},
                        ]
                    },
                    "options": {
                        "timeout": 5000,
                        "response": {"response": {"neverError": True}},
                    },
                },
            },
            {
                "id": n_tg,
                "name": "Telegram Plano",
                "type": "n8n-nodes-base.telegram",
                "typeVersion": 1.2,
                "position": [1000, 300],
                "parameters": {
                    "chatId": TELEGRAM_CHAT_ID,
                    "text": "={{ $('Seleccionar Produto + Formatar Plano').first().json.text }}",
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
                "name": "Telegram Erro",
                "type": "n8n-nodes-base.telegram",
                "typeVersion": 1.2,
                "position": [250, 600],
                "parameters": {
                    "chatId": TELEGRAM_CHAT_ID,
                    # FIX: expressão pura ={{ }}
                    "text": "={{ '❌ WF-04 Erro\\n' + ($json.execution?.error?.message || $json.error?.message || 'Erro desconhecido') }}",
                    "additionalFields": {"parse_mode": "HTML"},
                },
                "credentials": {
                    "telegramApi": {"id": TELEGRAM_CRED_ID, "name": TELEGRAM_CRED_NAME}
                },
            },
        ],
        "connections": {
            # FIX: dois schedules separados → ambos para GET Shopify
            "Schedule Terça 09:00": {"main": [[{"node": "GET Shopify Produtos", "type": "main", "index": 0}]]},
            "Schedule Sexta 09:00": {"main": [[{"node": "GET Shopify Produtos", "type": "main", "index": 0}]]},
            # Webhook bypassa Shopify e vai directo ao Code
            "Webhook Test":         {"main": [[{"node": "Seleccionar Produto + Formatar Plano", "type": "main", "index": 0}]]},
            "GET Shopify Produtos":  {"main": [[{"node": "Seleccionar Produto + Formatar Plano", "type": "main", "index": 0}]]},
            "Seleccionar Produto + Formatar Plano": {"main": [[{"node": "Notificar WF-03", "type": "main", "index": 0}]]},
            "Notificar WF-03":       {"main": [[{"node": "Telegram Plano", "type": "main", "index": 0}]]},
            "Error Trigger":         {"main": [[{"node": "Telegram Erro", "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


if __name__ == "__main__":
    # Apagar versão anterior dinamicamente por nome
    old_id = get_wf_id_by_name("WF-04")
    if old_id:
        s = delete_workflow(old_id)
        print(f"Apagado WF-04 anterior (ID={old_id}): HTTP {s}")

    try:
        wf_id = create_workflow_api(workflow_wf04())
        r = httpx.get(f"{N8N_URL}/api/v1/workflows/{wf_id}", headers=HEADERS, timeout=10)
        active = r.json().get("active", False) if r.status_code == 200 else "?"
        print(f"{'✅' if active else '⚠️ '} WF-04 Content Scheduler — ID={wf_id} active={active}")
        print(f"Webhook test: POST http://localhost:5678/webhook/wf-04-test")
        print(f'Payload: {{"product_info":"Suporte Laptop|29.99|Melhora postura"}}')
    except Exception as e:
        print(f"❌ WF-04 — {e}")
