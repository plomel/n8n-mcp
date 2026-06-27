"""Testa trigger e lista execuções dos WF-01."""
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
API_KEY = os.getenv("N8N_API_KEY", "")
HEADERS = {"X-N8N-API-KEY": API_KEY}

WF_IDS = {
    "WF-01a Health Check":  "xWpLe3Aj1q94nvLM",
    "WF-01b Daily Summary": "6aw2BKtD94UPQyxx",
}

for name, wf_id in WF_IDS.items():
    print(f"\n=== {name} ({wf_id}) ===")
    # Listar execuções
    r = httpx.get(f"{N8N_URL}/api/v1/executions?workflowId={wf_id}&limit=5", headers=HEADERS, timeout=15)
    data = r.json()
    execs = data.get("data", [])
    print(f"Execucoes recentes: {len(execs)}")
    for e in execs:
        print(f"  ID={e['id']} status={e['status']} finished={e['finished']} at={e.get('startedAt','?')}")

    # Tentar endpoint de execucao
    endpoints_to_try = [
        ("POST", f"{N8N_URL}/api/v1/workflows/{wf_id}/run",     {"runData": {}}),
        ("POST", f"{N8N_URL}/api/v1/workflows/{wf_id}/execute", {}),
        ("POST", f"{N8N_URL}/api/v1/executions",                {"workflowId": wf_id}),
    ]
    print("\nTentando endpoints de trigger:")
    for method, url, body in endpoints_to_try:
        try:
            resp = httpx.post(url, headers={**HEADERS, "Content-Type": "application/json"}, json=body, timeout=10)
            print(f"  {method} {url.split('/api/v1/')[-1]} → {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"  {method} {url.split('/api/v1/')[-1]} → ERRO: {e}")
