"""
FASE 4 — Testa se os Error Trigger + Telegram Error funcionam correctamente.

Estratégia:
1. Verifica se execuções de erro passadas tiveram o Telegram Error a correr
2. Simula um erro parando bot_state_api e disparando WF-01a
3. Verifica se o Telegram Error enviou mensagem
"""
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
HEADERS = {"X-N8N-API-KEY": API_KEY}


def get_wf_id(name_fragment: str) -> str:
    r = httpx.get(f"{N8N_URL}/api/v1/workflows?limit=50", headers=HEADERS, timeout=10)
    for wf in r.json().get("data", []):
        if name_fragment in wf.get("name", ""):
            return wf["id"]
    raise RuntimeError(f"Workflow '{name_fragment}' não encontrado")


def check_exec_error_trigger(exec_id: str) -> dict:
    """Retorna info sobre se Telegram Error correu numa execução."""
    r = httpx.get(f"{N8N_URL}/api/v1/executions/{exec_id}?includeData=true", headers=HEADERS, timeout=15)
    full = r.json()
    run_data = full.get("data", {}).get("resultData", {}).get("runData", {})
    result = {
        "exec_id": exec_id,
        "status": full.get("status"),
        "wf_id": full.get("workflowId"),
        "error_trigger_ran": "Error Trigger" in run_data,
        "telegram_error_ran": "Telegram Error" in run_data or "Telegram Erro" in run_data,
        "nodes_ran": list(run_data.keys()),
        "error_msg": full.get("data", {}).get("resultData", {}).get("error", {}).get("message", ""),
    }
    # Verificar qual nó falhou
    for node, runs in run_data.items():
        last = (runs or [{}])[-1]
        err = last.get("error")
        if err:
            result["failed_node"] = node
            result["failed_msg"] = err.get("message", "?")
    return result


print("=== FASE 4 — Teste Error Triggers ===\n")

WF_01A_ID = get_wf_id("WF-01a")
print(f"WF-01a: {WF_01A_ID}\n")

# 1. Verificar execuções de erro passadas
print("1. Verificando execuções de erro passadas de WF-01a...")
r = httpx.get(f"{N8N_URL}/api/v1/executions?workflowId={WF_01A_ID}&limit=10", headers=HEADERS, timeout=10)
execs = r.json().get("data", [])
error_execs = [e for e in execs if e.get("status") == "error"]
print(f"   Execuções com erro: {len(error_execs)}")

for e in error_execs[:3]:
    info = check_exec_error_trigger(e["id"])
    tg_status = "✅ Telegram Error enviou" if info["telegram_error_ran"] else "❌ Telegram Error NÃO correu"
    print(f"   Exec {e['id']}: {info['status']} | Nós: {info['nodes_ran']} | {tg_status}")
    if info.get("failed_node"):
        print(f"     Falhou em: {info['failed_node']} — {info.get('failed_msg','?')[:80]}")

# 2. Simular erro real: parar bot_state_api e disparar WF-01a
print("\n2. Simulando erro real — a parar bot_state_api temporariamente...")
# Encontrar PID da API
try:
    r_ping = httpx.get("http://localhost:8766/health", timeout=3)
    api_pid = r_ping.json().get("pid")
    print(f"   bot_state_api PID: {api_pid}")

    # Parar
    subprocess.run(["taskkill", "/PID", str(api_pid), "/F"], capture_output=True)
    time.sleep(1)

    # Confirmar que parou
    try:
        httpx.get("http://localhost:8766/ping", timeout=2)
        print("   ⚠️  API ainda a responder (pode ter reiniciado)")
    except Exception:
        print("   ✅ API parou")

    # Disparar WF-01a
    print("\n3. Disparando WF-01a (vai falhar em GET Bot Status)...")
    r2 = httpx.post(f"{N8N_URL}/webhook/wf-01a-test", json={"source": "error-test"}, timeout=10)
    print(f"   Webhook → {r2.status_code}")

    time.sleep(6)

    # Verificar a execução mais recente
    r3 = httpx.get(f"{N8N_URL}/api/v1/executions?workflowId={WF_01A_ID}&limit=1", headers=HEADERS, timeout=10)
    latest = r3.json().get("data", [])
    if latest:
        info = check_exec_error_trigger(latest[0]["id"])
        print(f"\n4. Resultado:")
        print(f"   Exec {info['exec_id']}: status={info['status']}")
        print(f"   Nós que correram: {info['nodes_ran']}")
        tg_ran = info["telegram_error_ran"]
        print(f"   Telegram Error: {'✅ FUNCIONOU' if tg_ran else '❌ NÃO FUNCIONOU'}")
        if info.get("failed_node"):
            print(f"   Falhou em: {info['failed_node']} — {info.get('failed_msg','')[:80]}")

        if not tg_ran:
            print("\n   ⚠️  Error Trigger não disparou — o formato pode estar errado")
            print("   Verificar: nó Error Trigger está ligado ao Telegram Error nas connections?")
    else:
        print("   Nenhuma execução encontrada")

except Exception as ex:
    print(f"   Erro no teste: {ex}")

finally:
    # Reiniciar bot_state_api
    print("\n5. Reiniciando bot_state_api...")
    subprocess.Popen(
        [sys.executable, r"C:\Desenvolvimento\trading-bot\bot_state_api.py"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    try:
        r4 = httpx.get("http://localhost:8766/health", timeout=4)
        print(f"   ✅ bot_state_api voltou (PID={r4.json().get('pid')})")
    except Exception:
        print("   ❌ bot_state_api não reiniciou — inicia manualmente")
