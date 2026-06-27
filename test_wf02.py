"""Testa WF-02 via webhook. Precisa de bot_state_api.py a correr."""
import httpx
import os
import time
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
API_KEY = os.getenv("N8N_API_KEY", "")
HEADERS = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}

WF_02_ID = None  # preenchido após criação


def start_bot_api():
    proc = subprocess.Popen(
        [sys.executable, r"C:\Desenvolvimento\trading-bot\bot_state_api.py"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    try:
        r = httpx.get("http://localhost:8766/health", timeout=3)
        print(f"  bot_state_api: ✅ a correr (PID {proc.pid})")
        # Testar /briefing
        rb = httpx.get("http://localhost:8766/briefing", timeout=3)
        b = rb.json()
        print(f"  /briefing: bot_running={b.get('bot_running')} last_video={b.get('last_video')}")
        return proc
    except Exception as e:
        print(f"  bot_state_api: ❌ erro — {e}")
        return proc


def get_latest_execution(wf_id: str, timeout: int = 20) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = httpx.get(f"{N8N_URL}/api/v1/executions?workflowId={wf_id}&limit=1", headers=HEADERS, timeout=10)
        execs = r.json().get("data", [])
        if execs and execs[0].get("finished"):
            return execs[0]
        time.sleep(2)
    return {}


def print_exec_detail(exec_id: str):
    r = httpx.get(f"{N8N_URL}/api/v1/executions/{exec_id}?includeData=true", headers=HEADERS, timeout=15)
    full = r.json()
    print(f"  Status: {full.get('status', '?')}")
    run_data = full.get("data", {}).get("resultData", {}).get("runData", {})
    for node_name, runs in run_data.items():
        if not runs:
            continue
        last = runs[-1]
        err = last.get("error")
        if err:
            msg = err.get("message", "?")
            print(f"  ❌ {node_name}: {msg}")
        else:
            out = last.get("data", {}).get("main", [[]])
            if out and out[0]:
                item = out[0][0].get("json", {})
                if "text" in item:
                    print(f"  ✅ {node_name}: text={str(item['text'])[:120]!r}")
                elif "ok" in item:
                    print(f"  ✅ {node_name}: Telegram ok (msg_id={item.get('result', {}).get('message_id', '?')})")
                else:
                    print(f"  ✅ {node_name}: {str(item)[:100]}")


# Ler ID do WF-02 criado
print("=== Teste WF-02 Morning Briefing ===\n")
r = httpx.get(f"{N8N_URL}/api/v1/workflows?limit=50", headers={"X-N8N-API-KEY": API_KEY}, timeout=10)
for wf in r.json().get("data", []):
    if "WF-02" in wf.get("name", ""):
        WF_02_ID = wf["id"]
        print(f"WF-02 encontrado: ID={WF_02_ID} active={wf.get('active')}")
        break

if not WF_02_ID:
    print("❌ WF-02 não encontrado — corre create_wf_02_morning_briefing.py primeiro")
    sys.exit(1)

print("\n1. Iniciando bot_state_api.py...")
proc = start_bot_api()

try:
    print("\n2. Acionando WF-02 via webhook...")
    r = httpx.post(f"{N8N_URL}/webhook/wf-02-test", json={"source": "test"}, timeout=10)
    print(f"   Webhook → {r.status_code}: {r.text[:80]}")

    time.sleep(3)
    exec_data = get_latest_execution(WF_02_ID, timeout=20)
    if exec_data:
        print(f"   Execução ID: {exec_data['id']}")
        print_exec_detail(exec_data["id"])
    else:
        print("   ⚠️  Nenhuma execução registada em 20s")

finally:
    proc.terminate()
    print("\nbot_state_api parado.")
