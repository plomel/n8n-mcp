import httpx
import json
from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()
api_key = os.getenv('N8N_API_KEY')
n8n_url = os.getenv('N8N_URL', 'http://localhost:5678')

print('='*80)
print('N8N AUDITORIA DE WORKFLOWS')
print('='*80)
print(f'API Key presente: {bool(api_key)}')
print(f'N8N URL: {n8n_url}')
print()

client = httpx.Client(base_url=n8n_url, headers={'X-N8N-API-KEY': api_key})

# Query 1: List all workflows
print('QUERY 1: GET /api/v1/workflows?limit=50')
print('-'*80)
try:
    resp = client.get('/api/v1/workflows?limit=50')
    resp.raise_for_status()
    workflows = resp.json()
    print(f'Status: {resp.status_code}')
    print(f'Total workflows: {len(workflows.get("data", []))}')
    print()
    
    for wf in workflows.get('data', []):
        print(f'  ID: {wf.get("id")} | Name: {wf.get("name")} | Active: {wf.get("active")}')
    
    wf_ids = [wf['id'] for wf in workflows.get('data', []) if '[WF-' in wf.get('name', '')]
    print()
    print(f'Workflows com [WF- no nome: {len(wf_ids)} encontrados')
    
except Exception as e:
    print(f'ERRO: {e}')
    wf_ids = []

print()
print('='*80)
print('QUERY 2: GET /api/v1/workflows/{id} para workflows [WF-*]')
print('-'*80)

for wf_id in wf_ids:
    try:
        resp = client.get(f'/api/v1/workflows/{wf_id}')
        resp.raise_for_status()
        wf = resp.json()
        print()
        print(f'Workflow ID: {wf_id}')
        print(f'  Name: {wf.get("name")}')
        print(f'  Active: {wf.get("active")}')
        print(f'  Nodes: {len(wf.get("nodes", []))}')
        for node in wf.get('nodes', []):
            print(f'    - {node.get("name")} (type: {node.get("type")})')
        print(f'  Webhook paths:')
        has_webhook = False
        for node in wf.get('nodes', []):
            if node.get('type') == 'n8n-nodes-base.webhook':
                path = node.get('parameters', {}).get('path', 'N/A')
                print(f'    - {path}')
                has_webhook = True
        if not has_webhook:
            print(f'    (nenhum webhook configurado)')
    except Exception as e:
        print(f'ERRO ao obter workflow {wf_id}: {e}')

print()
print('='*80)
print('QUERY 3: GET /api/v1/executions?limit=20')
print('-'*80)

try:
    resp = client.get('/api/v1/executions?limit=20')
    resp.raise_for_status()
    executions = resp.json()
    print(f'Status: {resp.status_code}')
    print(f'Total executions: {len(executions.get("data", []))}')
    print()
    
    error_exec_ids = []
    for exec in executions.get('data', []):
        status = exec.get('status')
        print(f'  ID: {exec.get("id")} | WorkflowID: {exec.get("workflowId")} | Status: {status}')
        if status != 'success':
            error_exec_ids.append(exec.get('id'))
    
except Exception as e:
    print(f'ERRO: {e}')
    error_exec_ids = []

print()
print('='*80)
print('QUERY 4: GET /api/v1/executions/{id} para execuções com erro')
print('-'*80)

if error_exec_ids:
    for exec_id in error_exec_ids[:5]:
        try:
            resp = client.get(f'/api/v1/executions/{exec_id}?includeData=true')
            resp.raise_for_status()
            exec_data = resp.json()
            print()
            print(f'Execution ID: {exec_id}')
            print(f'  Status: {exec_data.get("status")}')
            print(f'  WorkflowID: {exec_data.get("workflowId")}')
            if exec_data.get('data'):
                print(f'  Data: {json.dumps(exec_data.get("data"), indent=4)[:1000]}')
        except Exception as e:
            print(f'ERRO ao obter execução {exec_id}: {e}')
else:
    print('Nenhuma execução com erro encontrada.')

print()
print('='*80)
print('QUERY 5: Verifying webhook paths')
print('-'*80)

webhooks = [
    'http://localhost:5678/webhook/wf-01a-test',
    'http://localhost:5678/webhook/wf-01b-test',
    'http://localhost:5678/webhook/wf-02-test',
    'http://localhost:5678/webhook/wf-04-test',
]

for webhook_url in webhooks:
    try:
        resp = httpx.post(webhook_url, json={'source': 'audit'}, timeout=5.0)
        print(f'{webhook_url}')
        print(f'  Status: {resp.status_code}')
    except httpx.ConnectError as e:
        print(f'{webhook_url}')
        print(f'  Status: ERRO (Conexão) - {str(e)[:100]}')
    except Exception as e:
        print(f'{webhook_url}')
        print(f'  Status: ERRO - {str(e)[:100]}')

print()
print('='*80)
print('FIM DA AUDITORIA')
print('='*80)
