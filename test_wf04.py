"""Testa WF-04 via webhook com produto manual. Verifica que WF-03 também executa sem erro."""
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


def get_latest_exec(wf_id: str, since_ts: float, timeout: int = 20) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = httpx.get(f"{N8N_URL}/api/v1/executions?workflowId={wf_id}&limit=1", headers=HEADERS, timeout=10)
        execs = r.json().get("data", [])
        if execs and execs[0].get("finished"):
            return execs[0]
        time.sleep(2)
    return {}


def print_exec(exec_id: str):
    r = httpx.get(f"{N8N_URL}/api/v1/executions/{exec_id}?includeData=true", headers=HEADERS, timeout=15)
    full = r.json()
    print(f"  Status: {full.get('status')}")
    run_data = full.get("data", {}).get("resultData", {}).get("runData", {})
    for node_name, runs in run_data.items():
        last = runs[-1] if runs else {}
        err = last.get("error")
        if err:
            print(f"  ❌ {node_name}: {err.get('message', '?')}")
        else:
            out = last.get("data", {}).get("main", [[]])
            item = out[0][0].get("json", {}) if (out and out[0]) else {}
            if "text" in item:
                print(f"  ✅ {node_name}: {str(item['text'])[:100]!r}")
            elif "ok" in item:
                print(f"  ✅ {node_name}: Telegram ok (msg_id={item.get('result', {}).get('message_id', '?')})")
            elif "message" in item:
                print(f"  ✅ {node_name}: {item['message']}")
            else:
                print(f"  ✅ {node_name}: {str(item)[:80]}")


print("=== Teste WF-04 + WF-03 (integração) ===\n")

WF_04_ID = get_wf_id("WF-04")
WF_03_ID = get_wf_id("WF-03")
print(f"WF-04: {WF_04_ID}")
print(f"WF-03: {WF_03_ID}")

t0 = time.time()
payload = {"product_info": "Suporte Laptop Ergonómico|29.99|Melhora postura e reduz dor nas costas"}
r = httpx.post(f"{N8N_URL}/webhook/wf-04-test", json=payload, timeout=10)
print(f"\nWF-04 webhook → {r.status_code}: {r.text[:60]}")

time.sleep(5)

print("\n--- WF-04 ---")
exec4 = get_latest_exec(WF_04_ID, t0, timeout=20)
if exec4:
    print(f"Exec ID: {exec4['id']}")
    print_exec(exec4["id"])
else:
    print("⚠️  Nenhuma execução WF-04 em 20s")

print("\n--- WF-03 (disparado por WF-04) ---")
exec3 = get_latest_exec(WF_03_ID, t0, timeout=15)
if exec3:
    print(f"Exec ID: {exec3['id']}")
    print_exec(exec3["id"])
else:
    print("⚠️  Nenhuma execução WF-03 detectada")
