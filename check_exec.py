"""Mostra detalhes de execuções recentes."""
import httpx, os, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
API_KEY = os.getenv("N8N_API_KEY", "")
HEADERS = {"X-N8N-API-KEY": API_KEY}

for exec_id in ["16", "17", "18", "19", "20"]:
    print(f"\n=== Execução {exec_id} ===")
    r = httpx.get(f"{N8N_URL}/api/v1/executions/{exec_id}?includeData=true", headers=HEADERS, timeout=15)
    full = r.json()
    print(f"  status={full.get('status')} finished={full.get('finished')}")
    print(f"  workflowId={full.get('workflowId')}")
    run_data = full.get("data", {}).get("resultData", {}).get("runData", {})
    if not run_data:
        print("  runData: vazio ou não acessível")
        # Mostrar a estrutura completa para debug
        data_keys = list(full.get("data", {}).keys())
        print(f"  data keys: {data_keys}")
    else:
        for node_name, runs in run_data.items():
            if not runs:
                continue
            last = runs[-1]
            err = last.get("error")
            if err:
                print(f"  ❌ {node_name}: {err.get('message','?')}")
            else:
                output = last.get("data", {}).get("main", [[]])
                first_item = output[0][0].get("json", {}) if (output and output[0]) else {}
                preview = json.dumps(first_item, ensure_ascii=False)[:120]
                print(f"  ✅ {node_name}: {preview}")
