import httpx
import json
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('N8N_API_KEY')
n8n_url = os.getenv('N8N_URL', 'http://localhost:5678')

client = httpx.Client(base_url=n8n_url, headers={'X-N8N-API-KEY': api_key})

print('='*80)
print('AUDITORIA DETALHADA DE ERROS')
print('='*80)
print()

# Get all error executions
resp = client.get('/api/v1/executions?limit=50')
executions = resp.json()

error_execs = [e for e in executions.get('data', []) if e.get('status') == 'error']
print(f'Total de execuções com erro: {len(error_execs)}')
print()

# Group by workflow
from collections import defaultdict
errors_by_wf = defaultdict(list)
for exec in error_execs:
    errors_by_wf[exec.get('workflowId')].append(exec.get('id'))

# Get workflow names
wf_resp = client.get('/api/v1/workflows?limit=50')
workflows = wf_resp.json()
wf_names = {wf['id']: wf['name'] for wf in workflows.get('data', [])}

print('ERROS POR WORKFLOW:')
print('-'*80)
for wf_id, exec_ids in sorted(errors_by_wf.items()):
    wf_name = wf_names.get(wf_id, 'UNKNOWN')
    print()
    print(f'Workflow: {wf_name}')
    print(f'ID: {wf_id}')
    print(f'Total de erros: {len(exec_ids)}')
    
    # Get details of first 3 errors
    for exec_id in exec_ids[:3]:
        try:
            resp = client.get(f'/api/v1/executions/{exec_id}?includeData=true')
            exec_data = resp.json()
            error = exec_data.get('data', {}).get('resultData', {}).get('error', {})
            
            print(f'  Execução #{exec_id}:')
            if isinstance(error, dict):
                if error.get('message'):
                    print(f'    Mensagem: {error.get("message")[:200]}')
                if error.get('stack'):
                    lines = error.get('stack', '').split('\n')
                    print(f'    Stack: {lines[0][:150]}')
            else:
                print(f'    Erro: {str(error)[:200]}')
        except Exception as e:
            print(f'  Execução #{exec_id}: Erro ao ler - {e}')

print()
print('='*80)
print('VERIFICAÇÃO DE CONECTIVIDADE')
print('='*80)
print()

# Check if trading bot can reach its target
targets = [
    ('http://host.docker.internal:8766/status', 'Trading Bot Status Endpoint'),
    ('http://localhost:5678', 'N8N Local'),
]

for url, desc in targets:
    try:
        resp = httpx.get(url, timeout=3.0)
        print(f'{desc} ({url})')
        print(f'  Status: {resp.status_code}')
    except httpx.ConnectError:
        print(f'{desc} ({url})')
        print(f'  Status: ERRO - Conexão recusada')
    except Exception as e:
        print(f'{desc} ({url})')
        print(f'  Status: ERRO - {str(e)[:80]}')

