"""Testa WF-03 com payload simulado de yt2viral."""
import httpx
import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
API_KEY = os.getenv("N8N_API_KEY", "")
HEADERS = {"X-N8N-API-KEY": API_KEY}


def get_wf_id(name_fragment: str) -> str:
    r = httpx.get(f"{N8N_URL}/api/v1/workflows?limit=50", headers=HEADERS, timeout=10)
    for wf in r.json().get("data", []):
        if name_fragment in wf.get("name", ""):
            return wf["id"]
    raise RuntimeError(f"Workflow '{name_fragment}' não encontrado")


print("=== Teste WF-03 Upload Automator ===\n")

WF_03_ID = get_wf_id("WF-03")
print(f"WF-03: {WF_03_ID}")

payload = {
    "videoId": "7RaC2nKBqv4",
    "mp4Path": r"C:\Desenvolvimento\viral-videos\output\7RaC2nKBqv4_viral.mp4",
    "title": "Como Estudar de Forma Eficiente",
    "durationS": "54.3",
    "reason": "Maior densidade de conteudo educativo no segmento",
}

r = httpx.post(f"{N8N_URL}/webhook/yt2viral-ready", json=payload, timeout=10)
print(f"Webhook → {r.status_code}: {r.text[:80]}")

time.sleep(4)

r2 = httpx.get(f"{N8N_URL}/api/v1/executions?workflowId={WF_03_ID}&limit=1", headers=HEADERS, timeout=10)
execs = r2.json().get("data", [])
if not execs:
    print("❌ Nenhuma execução encontrada")
    exit(1)

exec_id = execs[0]["id"]
finished = execs[0].get("finished")
print(f"Execução ID: {exec_id} finished={finished}")

r3 = httpx.get(f"{N8N_URL}/api/v1/executions/{exec_id}?includeData=true", headers=HEADERS, timeout=15)
full = r3.json()
print(f"Status: {full.get('status')}")

run_data = full.get("data", {}).get("resultData", {}).get("runData", {})
for node_name, runs in run_data.items():
    if not runs:
        continue
    last = runs[-1]
    err = last.get("error")
    if err:
        print(f"  ❌ {node_name}: {err.get('message', '?')}")
    else:
        out = last.get("data", {}).get("main", [[]])
        item = out[0][0].get("json", {}) if (out and out[0]) else {}
        if "text" in item:
            print(f"  ✅ {node_name}: {str(item['text'])[:120]!r}")
        elif "ok" in item:
            msg_id = item.get("result", {}).get("message_id", "?")
            print(f"  ✅ {node_name}: Telegram ok (msg_id={msg_id})")
        else:
            print(f"  ✅ {node_name}: {str(item)[:100]}")
