"""
setup_check.py — Verifica API n8n, lista credenciais e variáveis disponíveis.
Correr antes de criar qualquer workflow.
"""
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
API_KEY = os.getenv("N8N_API_KEY", "")
HEADERS = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}


def check_api():
    try:
        r = httpx.get(f"{N8N_URL}/api/v1/workflows", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            wfs = r.json().get("data", [])
            print(f"✅ API OK — {len(wfs)} workflows existentes")
            for wf in wfs:
                print(f"   [{wf['id']}] {wf['name']} — {'🟢 activo' if wf.get('active') else '⚪ inactivo'}")
        else:
            print(f"❌ API erro {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"❌ Ligação falhou: {e}")


def check_credentials():
    try:
        r = httpx.get(f"{N8N_URL}/api/v1/credentials", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            creds = r.json().get("data", [])
            print(f"\n✅ Credenciais ({len(creds)}):")
            for c in creds:
                print(f"   [{c['id']}] {c['name']} ({c['type']})")
            return {c["name"]: c["id"] for c in creds}
        else:
            print(f"❌ Credenciais erro {r.status_code}: {r.text[:200]}")
            return {}
    except Exception as e:
        print(f"❌ Credenciais falhou: {e}")
        return {}


def check_variables():
    try:
        r = httpx.get(f"{N8N_URL}/api/v1/variables", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            variables = r.json().get("data", [])
            print(f"\n✅ Variáveis n8n ({len(variables)}):")
            for v in variables:
                print(f"   {v['key']} = {v['value'][:30] if v.get('value') else '(vazio)'}")
        else:
            print(f"⚠️  Variáveis não acessíveis ({r.status_code})")
    except Exception as e:
        print(f"⚠️  Variáveis: {e}")


def check_logs_dir():
    logs = Path(r"C:\n8n-logs")
    logs.mkdir(exist_ok=True)
    print(f"\n✅ C:\\n8n-logs\\ existe: {logs.exists()}")


if __name__ == "__main__":
    print("=" * 50)
    print("n8n Setup Check")
    print("=" * 50)
    check_api()
    creds = check_credentials()
    check_variables()
    check_logs_dir()
    print("\n" + "=" * 50)
    print("IDs para copiar para os scripts de workflow:")
    for name, cid in creds.items():
        print(f"  {name!r}: {cid!r}")
