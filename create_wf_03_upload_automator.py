"""
WF-03 — YT2Viral Upload Automator (v2 — fallback robusto)

Fixes aplicados:
- Code node não lança throw — usa fallback gracioso quando videoId em falta
- Error Trigger usa expressão pura ={{ }} em vez de =texto misto
- Suporta payloads de WF-04 (placeholder) sem falhar

yt2viral.ts chama: POST http://localhost:5678/webhook/yt2viral-ready
Payload: { videoId, mp4Path, title, durationS, reason }
WF-04 chama com: { videoId: "wf04-placeholder", ... }
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


def workflow_wf03():
    n_wh   = uid()
    n_code = uid()
    n_tg   = uid()
    n_err  = uid()
    n_tgerr = uid()

    return {
        "name": "[WF-03] YT2Viral — Notificação de Vídeo Pronto",
        "nodes": [
            {
                "id": n_wh,
                "name": "Webhook yt2viral-ready",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [0, 300],
                "webhookId": uid(),
                "parameters": {
                    "httpMethod": "POST",
                    "path": "yt2viral-ready",
                    "responseMode": "onReceived",
                    "options": {},
                },
            },
            {
                "id": n_code,
                "name": "Formatar Notificação",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [250, 300],
                "parameters": {
                    "mode": "runOnceForAllItems",
                    # FIX: sem throw — fallback gracioso para todos os campos
                    "jsCode": r"""
const raw  = $('Webhook yt2viral-ready').first().json;
const body = raw.body || raw;

const videoId  = body.videoId  || 'desconhecido';
const mp4Path  = body.mp4Path  || 'path não fornecido';
const title    = body.title    || videoId;
const duration = body.durationS || '?';
const reason   = body.reason   || '';

const isPlaceholder = videoId === 'wf04-placeholder' || videoId === 'desconhecido';
const fileName = mp4Path.split(/[\\/]/).pop() || mp4Path;

let lines = [];
if (isPlaceholder) {
  lines = [
    `📋 <b>WF-04 Plano Gerado</b>`,
    ``,
    `🛍️ Produto: ${title}`,
    ``,
    `⏳ Vídeo pendente (build_story_video.py + upload YouTube a configurar)`,
  ];
} else {
  lines = [
    `🎬 <b>Vídeo Viral Pronto!</b>`,
    ``,
    `📌 ID: ${videoId}`,
    `📁 Ficheiro: ${fileName}`,
    `⏱️ Duração: ${duration}s`,
    reason ? `💡 Motivo: ${reason.slice(0, 100)}` : null,
    ``,
    `⚠️ Upload YouTube: pendente (credenciais não configuradas)`,
    `📂 Path: ${mp4Path}`,
  ];
}

const text = lines.filter(l => l !== null).join('\n');
return [{ json: { text, videoId, mp4Path, title, isPlaceholder } }];
""",
                },
            },
            {
                "id": n_tg,
                "name": "Telegram Notificação",
                "type": "n8n-nodes-base.telegram",
                "typeVersion": 1.2,
                "position": [500, 300],
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
                "position": [0, 550],
                "parameters": {},
            },
            {
                "id": n_tgerr,
                "name": "Telegram Error",
                "type": "n8n-nodes-base.telegram",
                "typeVersion": 1.2,
                "position": [250, 550],
                "parameters": {
                    "chatId": TELEGRAM_CHAT_ID,
                    # FIX: expressão pura ={{ }} — mais fiável que =texto {{ expr }}
                    "text": "={{ '❌ WF-03 Erro\\n' + ($json.execution?.error?.message || $json.error?.message || 'Erro desconhecido') }}",
                    "additionalFields": {"parse_mode": "HTML"},
                },
                "credentials": {
                    "telegramApi": {"id": TELEGRAM_CRED_ID, "name": TELEGRAM_CRED_NAME}
                },
            },
        ],
        "connections": {
            "Webhook yt2viral-ready": {"main": [[{"node": "Formatar Notificação", "type": "main", "index": 0}]]},
            "Formatar Notificação":   {"main": [[{"node": "Telegram Notificação", "type": "main", "index": 0}]]},
            "Error Trigger":          {"main": [[{"node": "Telegram Error", "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


if __name__ == "__main__":
    # Apagar versão anterior
    old_id = get_wf_id_by_name("WF-03")
    if old_id:
        s = delete_workflow(old_id)
        print(f"Apagado WF-03 anterior (ID={old_id}): HTTP {s}")

    try:
        wf_id = create_workflow_api(workflow_wf03())
        r = httpx.get(f"{N8N_URL}/api/v1/workflows/{wf_id}", headers=HEADERS, timeout=10)
        active = r.json().get("active", False) if r.status_code == 200 else "?"
        print(f"{'✅' if active else '⚠️ '} WF-03 Upload Automator — ID={wf_id} active={active}")
        print(f"Webhook: POST http://localhost:5678/webhook/yt2viral-ready")
    except Exception as e:
        print(f"❌ WF-03 — {e}")
