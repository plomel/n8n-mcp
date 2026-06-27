import httpx
import json
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('N8N_API_KEY')
n8n_url = os.getenv('N8N_URL', 'http://localhost:5678')

client = httpx.Client(base_url=n8n_url, headers={'X-N8N-API-KEY': api_key})

print('='*100)
print('AUDITORIA: ENDPOINTS & HTTP REQUESTS NOS WORKFLOWS [WF-*]')
print('='*100)
print()

# Get WF-* workflows
wf_resp = client.get('/api/v1/workflows?limit=50')
workflows = wf_resp.json().get('data', [])
wf_targets = [w for w in workflows if '[WF-' in w.get('name', '')]

for wf in wf_targets:
    resp = client.get(f'/api/v1/workflows/{wf["id"]}')
    wf_full = resp.json()
    
    print(f'[{wf.get("name")}]')
    print(f'ID: {wf["id"]}')
    print()
    
    # Find HTTP Request nodes
    http_nodes = [n for n in wf_full.get('nodes', []) if n.get('type') == 'n8n-nodes-base.httpRequest']
    
    if http_nodes:
        print(f'HTTP Requests ({len(http_nodes)}):')
        for node in http_nodes:
            params = node.get('parameters', {})
            method = params.get('method', 'GET')
            url = params.get('url', 'N/A')
            timeout = params.get('timeout', 5)
            
            print(f'  Node: {node.get("name")}')
            print(f'    Method: {method}')
            print(f'    URL: {url}')
            print(f'    Timeout: {timeout}s')
            
            # Try to connect
            try:
                if method == 'GET':
                    resp = httpx.get(url, timeout=float(timeout))
                    print(f'    Status: {resp.status_code} ✓')
                elif method == 'POST':
                    resp = httpx.post(url, timeout=float(timeout), json={})
                    print(f'    Status: {resp.status_code} ✓')
                else:
                    print(f'    Status: Método {method} não testado')
            except httpx.ConnectError as e:
                print(f'    Status: ERRO - Conexão recusada')
            except httpx.TimeoutException as e:
                print(f'    Status: ERRO - Timeout')
            except Exception as e:
                print(f'    Status: ERRO - {str(e)[:80]}')
            print()
    else:
        print('  (nenhum HTTP Request configurado)')
    
    print()
    print('-'*100)
    print()
