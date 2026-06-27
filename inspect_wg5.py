"""Inspecciona o JSON WG-5 para ver nodes e credenciais necessárias."""
import json

with open(r"C:\Desenvolvimento\WorkGadget-Content\n8n-wg5-content-scheduler.json", encoding="utf-8") as f:
    wf = json.load(f)

print(f"Nome: {wf.get('name')}")
print(f"Settings: {wf.get('settings')}")
print("\nNodes:")
for n in wf.get("nodes", []):
    creds = n.get("credentials", {})
    node_type = n.get("type", "?")
    node_name = n.get("name", "?")
    print(f"  [{node_type}] {node_name}")
    if creds:
        for cred_type, cred_info in creds.items():
            print(f"    cred: {cred_type} → id={cred_info.get('id')} name={cred_info.get('name')}")

print("\nTipos únicos de nodes:")
types = sorted(set(n.get("type", "") for n in wf.get("nodes", [])))
for t in types:
    print(f"  {t}")
