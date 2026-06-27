"""Testa WF-01a e WF-01b via webhook. Precisa de bot_state_api.py a correr."""
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


def get_wf_id(name_fragment: str) -> str:
    r = httpx.get(f"{N8N_URL}/api/v1/workflows?limit=50", headers={"X-N8N-API-KEY": API_KEY}, timeout=10)
    for wf in r.json().get("data", []):
        if name_fragment in wf.get("name", ""):
            return wf["id"]
    raise RuntimeError(f"Workflow '{name_fragment}' não encontrado")


def start_bot_api():
    proc = subprocess.Popen(
        [sys.executable, r"C:\Desenvolvimento\trading-bot\bot_state_api.py"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    try:
        r = httpx.get("http://localhost:8766/health", timeout=3)
        print(f"  bot_state_api: ✅ a correr (PID {r.json().get('pid', proc.pid)})")
        return proc
    except Exception:
        print("  bot_state_api: ❌ não arrancou")
        return proc


def get_execution_details(wf_id: str, timeout: int = 15) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = httpx.get(f"{N8N_URL}/api/v1/executions?workflowId={wf_id}&limit=1", headers=HEADERS, timeout=10)
        execs = r.json().get("data", [])
        if execs and execs[0].get("finished"):
            return execs[0]
        time.sleep(2)
    return {}


def print_execution_detail(exec_id: str):
    r = httpx.get(f"{N8N_URL}/api/v1/executions/{exec_id}?includeData=true", headers=HEADERS, timeout=15)
    full = r.json()
    status = full.get("status", "?")
    print(f"  Status geral: {status}")
    run_data = full.get("data", {}).get("resultData", {}).get("runData", {})
    for node_name, runs in run_data.items():
        if not runs:
            continue
        last = runs[-1]
        err = last.get("error")
        if err:
            msg = err.get("message", "?")
            desc = err.get("description", "")
            print(f"  ❌ {node_name}: {msg}" + (f"\n     {desc[:100]}" if desc else ""))
        else:
            output = last.get("data", {}).get("main", [[]])
            if output and output[0]:
                first_json = output[0][0].get("json", {})
                if "text" in first_json:
                    preview = str(first_json["text"])[:100]
                    print(f"  ✅ {node_name}: text={preview!r}")
                elif "ok" in first_json or "bot_running" in first_json:
                    print(f"  ✅ {node_name}: {str(first_json)[:100]}")
                elif "ok" in first_json:
                    print(f"  ✅ {node_name}: Telegram ok (msg_id={first_json.get('result',{}).get('message_id','?')})")
                else:
                    print(f"  ✅ {node_name}: OK")


print("=== Teste WF-01 ===\n")

# IDs dinâmicos por nome
WF_01A_ID = get_wf_id("WF-01a")
WF_01B_ID = get_wf_id("WF-01b")
print(f"WF-01a: {WF_01A_ID}")
print(f"WF-01b: {WF_01B_ID}")

# Verificar se API já está a correr
api_running = False
try:
    httpx.get("http://localhost:8766/health", timeout=2)
    api_running = True
    print("\n1. bot_state_api já está a correr")
    proc = None
except Exception:
    print("\n1. Iniciando bot_state_api.py...")
    proc = start_bot_api()

try:
    print("\n2. Acionando WF-01b (Daily Summary) via webhook...")
    r = httpx.post(f"{N8N_URL}/webhook/wf-01b-test", json={"source": "test"}, timeout=10)
    print(f"   Webhook → {r.status_code}: {r.text[:100]}")

    time.sleep(3)
    exec_data = get_execution_details(WF_01B_ID, timeout=20)
    if exec_data:
        print(f"   Execução ID: {exec_data['id']}")
        print_execution_detail(exec_data["id"])
    else:
        print("   ⚠️  Nenhuma execução registada em 20s")

    print("\n3. Acionando WF-01a (Health Check) via webhook...")
    r2 = httpx.post(f"{N8N_URL}/webhook/wf-01a-test", json={"source": "test"}, timeout=10)
    print(f"   Webhook → {r2.status_code}: {r2.text[:100]}")

    time.sleep(3)
    exec_data2 = get_execution_details(WF_01A_ID, timeout=20)
    if exec_data2:
        print(f"   Execução ID: {exec_data2['id']}")
        print_execution_detail(exec_data2["id"])
    else:
        print("   ⚠️  Nenhuma execução registada em 20s")

finally:
    if proc:
        proc.terminate()
        print("\nbot_state_api parado.")
