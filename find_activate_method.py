"""Descobre o método HTTP correcto para activar workflows no n8n v2.17.3."""
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
API_KEY = os.getenv("N8N_API_KEY", "")
HEADERS = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
WF_ID = "xC2OqCUZ6frU7Zex"  # WF-01b


def try_method(method: str, url: str, body: dict = None):
    try:
        if method == "POST":
            r = httpx.post(url, headers=HEADERS, json=body or {}, timeout=10)
        elif method == "PUT":
            r = httpx.put(url, headers=HEADERS, json=body or {}, timeout=10)
        elif method == "PATCH":
            r = httpx.patch(url, headers=HEADERS, json=body or {}, timeout=10)
        else:
            return
        print(f"  {method} {url.split('localhost:5678')[-1]} → {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"  {method} → ERRO: {e}")


print("=== Testando métodos de activação ===")

# 1. POST ao /activate
try_method("POST", f"{N8N_URL}/api/v1/workflows/{WF_ID}/activate")

# 2. PATCH ao workflow com active=true no body
try_method("PATCH", f"{N8N_URL}/api/v1/workflows/{WF_ID}", {"active": True})

# 3. PUT ao workflow com active=true
# Primeiro precisamos de obter o workflow completo
r = httpx.get(f"{N8N_URL}/api/v1/workflows/{WF_ID}", headers=HEADERS, timeout=10)
if r.status_code == 200:
    wf_data = r.json()
    wf_data["active"] = True
    try_method("PUT", f"{N8N_URL}/api/v1/workflows/{WF_ID}", wf_data)

# 4. Verificar o workflow existente activo ([SYS]) para ver se a activação é possível via API
print("\n=== Verificar workflow SYS (já activo) ===")
r2 = httpx.get(f"{N8N_URL}/api/v1/workflows/0Zzft34xefoydTZ2", headers=HEADERS, timeout=10)
if r2.status_code == 200:
    d = r2.json()
    print(f"  [SYS] active={d['active']}")
    # Tentar reactivar o SYS (que já está activo)
    print("  Tentando PATCH /activate no SYS (já activo):")
    try_method("PATCH", f"{N8N_URL}/api/v1/workflows/0Zzft34xefoydTZ2/activate")

# 5. Estado final
print("\n=== Estado final WF-01b ===")
r3 = httpx.get(f"{N8N_URL}/api/v1/workflows/{WF_ID}", headers=HEADERS, timeout=10)
if r3.status_code == 200:
    print(f"  active={r3.json()['active']}")
