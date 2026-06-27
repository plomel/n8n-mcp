"""Activa workflows e testa via webhook."""
import httpx
import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
API_KEY = os.getenv("N8N_API_KEY", "")
HEADERS = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}

WF_01A = "xWpLe3Aj1q94nvLM"
WF_01B = "xC2OqCUZ6frU7Zex"

print("=== Estado actual ===")
for wf_id in [WF_01A, WF_01B]:
    r = httpx.get(f"{N8N_URL}/api/v1/workflows/{wf_id}", headers=HEADERS, timeout=10)
    if r.status_code == 200:
        d = r.json()
        print(f"  [{wf_id}] {d['name']} — active={d['active']}")
    else:
        print(f"  [{wf_id}] HTTP {r.status_code}")

print("\n=== Activar WF-01b ===")
r = httpx.patch(f"{N8N_URL}/api/v1/workflows/{WF_01B}/activate", headers=HEADERS, timeout=15)
print(f"  activate → {r.status_code}: {r.text[:300]}")

time.sleep(2)

print("\n=== Testar webhook WF-01b ===")
r = httpx.post(f"{N8N_URL}/webhook/wf-01b-test", json={"source": "test"}, timeout=15)
print(f"  webhook → {r.status_code}: {r.text[:300]}")

print("\n=== Execuções recentes WF-01b ===")
time.sleep(3)
r = httpx.get(f"{N8N_URL}/api/v1/executions?workflowId={WF_01B}&limit=3", headers=HEADERS, timeout=15)
data = r.json().get("data", [])
print(f"  {len(data)} execucoes")
for e in data:
    print(f"  ID={e['id']} status={e['status']} at={e.get('startedAt','?')}")
    # Verificar detalhes
    r2 = httpx.get(f"{N8N_URL}/api/v1/executions/{e['id']}", headers=HEADERS, timeout=15)
    full = r2.json()
    run_data = full.get("data", {}).get("resultData", {}).get("runData", {})
    for node_name, node_runs in run_data.items():
        if not node_runs:
            continue
        last = node_runs[-1]
        err = last.get("error")
        if err:
            print(f"    ❌ {node_name}: {err.get('message','?')[:100]}")
        else:
            output = last.get("data", {}).get("main", [[]])
            if output and output[0]:
                first = output[0][0].get("json", {})
                stdout = first.get("stdout", "")
                if stdout:
                    print(f"    ✅ {node_name}: stdout={stdout[:80]!r}")
                else:
                    print(f"    ✅ {node_name}: OK (sem stdout)")
