import httpx
import json
from dotenv import load_dotenv
import os
from collections import defaultdict

load_dotenv()
api_key = os.getenv('N8N_API_KEY')
n8n_url = os.getenv('N8N_URL', 'http://localhost:5678')

client = httpx.Client(base_url=n8n_url, headers={'X-N8N-API-KEY': api_key})

print('='*100)
print('RELATÓRIO COMPLETO DE AUDITORIA N8N — ESTADO REAL DOS WORKFLOWS')
print('='*100)
print()

# SECTION 1: Overview
print('SECTION 1: VISÃO GERAL')
print('-'*100)

wf_resp = client.get('/api/v1/workflows?limit=50')
workflows_data = wf_resp.json()
all_workflows = workflows_data.get('data', [])

active_workflows = [w for w in all_workflows if w.get('active')]
inactive_workflows = [w for w in all_workflows if not w.get('active')]

print(f'Total de workflows: {len(all_workflows)}')
print(f'  - Ativos: {len(active_workflows)}')
print(f'  - Inativos: {len(inactive_workflows)}')
print()

# SECTION 2: WF-* Workflows Details
print('SECTION 2: WORKFLOWS [WF-*] — ESTADO DETALHADO')
print('-'*100)

wf_targets = [w for w in all_workflows if '[WF-' in w.get('name', '')]
wf_targets_by_id = {w['id']: w for w in wf_targets}

for wf in wf_targets:
    resp = client.get(f'/api/v1/workflows/{wf["id"]}')
    wf_full = resp.json()
    
    print()
    print(f'[{wf.get("name")}]')
    print(f'  ID: {wf["id"]}')
    print(f'  Status: {"ATIVO" if wf.get("active") else "INATIVO"}')
    print(f'  Nodes ({len(wf_full.get("nodes", []))}):')
    
    for node in wf_full.get('nodes', []):
        node_type = node.get('type', 'UNKNOWN').replace('n8n-nodes-base.', '')
        print(f'    - {node.get("name"):40} ({node_type})', end='')
        
        # Check if webhook
        if node_type == 'webhook':
            path = node.get('parameters', {}).get('path', 'N/A')
            print(f' → webhook/{path}')
        else:
            print()
    
    # Check webhook connectivity
    print(f'  Webhook Test Paths:')
    for node in wf_full.get('nodes', []):
        if node.get('type') == 'n8n-nodes-base.webhook':
            path = node.get('parameters', {}).get('path', 'N/A')
            webhook_url = f'http://localhost:5678/webhook/{path}'
            try:
                resp = httpx.post(webhook_url, json={'source': 'audit'}, timeout=3.0)
                status_emoji = '✓' if resp.status_code == 200 else 'X'
                print(f'    {status_emoji} {webhook_url}: {resp.status_code}')
            except Exception as e:
                print(f'    X {webhook_url}: ERRO - {str(e)[:50]}')

print()
print()

# SECTION 3: Executions Analysis
print('SECTION 3: ANÁLISE DE EXECUÇÕES (últimas 20)')
print('-'*100)

exec_resp = client.get('/api/v1/executions?limit=20')
executions = exec_resp.json().get('data', [])

status_counts = defaultdict(int)
for exec in executions:
    status_counts[exec.get('status')] += 1

print()
print('Resumo de Status:')
for status, count in sorted(status_counts.items()):
    print(f'  - {status.upper()}: {count}')

# Find error executions
error_executions = [e for e in executions if e.get('status') != 'success']

if error_executions:
    print()
    print(f'Execuções com Erro ({len(error_executions)}):')
    print()
    
    for exec in error_executions[:10]:
        wf_id = exec.get('workflowId')
        wf_name = next((w.get('name') for w in all_workflows if w['id'] == wf_id), 'UNKNOWN')
        
        resp = client.get(f'/api/v1/executions/{exec.get("id")}?includeData=true')
        exec_data = resp.json()
        error = exec_data.get('data', {}).get('resultData', {}).get('error', {})
        
        print(f'  Execution ID: {exec.get("id")}')
        print(f'  Workflow: {wf_name} ({wf_id})')
        
        if isinstance(error, dict):
            msg = error.get('message', 'N/A')
            print(f'  Error: {msg[:150]}')
            if error.get('lineNumber'):
                print(f'  Line: {error.get("lineNumber")}')
        print()

print()
print()

# SECTION 4: Connectivity Issues
print('SECTION 4: PROBLEMAS DE CONECTIVIDADE IDENTIFICADOS')
print('-'*100)
print()

# Trading bot connectivity
print('Trading Bot External Dependencies:')
print(f'  Endpoint: http://host.docker.internal:8766/status')
try:
    resp = httpx.get('http://host.docker.internal:8766/status', timeout=2.0)
    print(f'  Status: {resp.status_code}')
except httpx.ConnectError:
    print(f'  Status: ERRO - Conexão recusada')
    print(f'  Impacto: WF-01a e WF-01b não conseguem obter status do bot')
except Exception as e:
    print(f'  Status: ERRO - {str(e)[:100]}')

print()
print()

# SECTION 5: Issues & Recommendations
print('SECTION 5: PROBLEMAS IDENTIFICADOS & RECOMENDAÇÕES')
print('-'*100)
print()

print('1. TRADING BOT OFFLINE (host.docker.internal:8766)')
print('   Workflows Afectados: WF-01a, WF-01b')
print('   Tipo: Erro crítico de conectividade')
print('   Status: 4 execuções falhadas (WF-01a), 1 falhada (WF-01b)')
print('   Ação: Iniciar trading bot ou verificar configuração de host.docker.internal')
print()

print('2. WF-03 - PAYLOAD INVÁLIDO (videoId missing)')
print('   Workflow: [WF-03] YT2Viral — Notificação de Vídeo Pronto')
print('   Tipo: Erro na validação de dados (node: "Formatar Notificação")')
print('   Status: 2 execuções falhadas')
print('   Ação: Verificar payload enviado para o webhook yt2viral-ready — campo videoId obrigatório')
print()

print('3. WF-02 - CONNECTIVITY ISSUE')
print('   Workflow: [WF-02] Daily Morning Briefing')
print('   Tipo: The service refused the connection')
print('   Status: 1 execução falhada')
print('   Ação: Verificar qual endpoint o node "GET Briefing" está tentando aceder')
print()

print('4. WORKFLOWS INATIVOS')
print(f'   Total: {len(inactive_workflows)} workflows inativos')
inactive_names = [w.get('name') for w in inactive_workflows]
for name in sorted(inactive_names)[:5]:
    print(f'     - {name}')
if len(inactive_names) > 5:
    print(f'     ... e mais {len(inactive_names) - 5}')
print()

print()
print('='*100)
print('FIM DO RELATÓRIO')
print('='*100)
