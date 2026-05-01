# Graph Report - Projects/Ativos/n8n-mcp  (2026-04-27)

## Corpus Check
- 7 files · ~8,471 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 38 nodes · 55 edges · 7 communities detected
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]

## God Nodes (most connected - your core abstractions)
1. `uid()` - 7 edges
2. `_api_get()` - 6 edges
3. `uid()` - 4 edges
4. `_api_post()` - 3 edges
5. `_update_workflow()` - 3 edges
6. `workflow_tb1_price_alert()` - 2 edges
7. `workflow_fat1_invoice_scanner()` - 2 edges
8. `workflow_tb2_daily_pnl()` - 2 edges
9. `workflow_wg1_product_discovery()` - 2 edges
10. `workflow_wg2_product_upload()` - 2 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Communities

### Community 0 - "Community 0"
Cohesion: 0.33
Nodes (8): create_workflows_phase2.py — Workflows Fase 2: WorkGadget + FAT-2 + TB-4 Correr:, uid(), workflow_fat2_monthly_audit(), workflow_tb4_risk_guardian(), workflow_wg1_product_discovery(), workflow_wg2_product_upload(), workflow_wg3_price_monitor(), workflow_wg4_weekly_report()

### Community 1 - "Community 1"
Cohesion: 0.43
Nodes (5): create_workflows.py — Cria os workflows iniciais no n8n via API REST Correr: pyt, uid(), workflow_fat1_invoice_scanner(), workflow_tb1_price_alert(), workflow_tb2_daily_pnl()

### Community 2 - "Community 2"
Cohesion: 0.33
Nodes (3): _api_delete(), _delete_workflow(), n8n_mcp.py — MCP Server local para controlar o n8n via Claude Code / Claude Desk

### Community 3 - "Community 3"
Cohesion: 0.29
Nodes (7): _api_get(), _api_put(), _get_execution(), _get_workflow(), _list_executions(), _list_workflows(), _update_workflow()

### Community 4 - "Community 4"
Cohesion: 0.67
Nodes (3): _api_post(), _create_workflow(), _trigger_workflow()

### Community 5 - "Community 5"
Cohesion: 1.0
Nodes (2): _activate_workflow(), _api_patch()

### Community 6 - "Community 6"
Cohesion: 1.0
Nodes (2): call_tool(), _dispatch()

## Knowledge Gaps
- **3 isolated node(s):** `create_workflows.py — Cria os workflows iniciais no n8n via API REST Correr: pyt`, `create_workflows_phase2.py — Workflows Fase 2: WorkGadget + FAT-2 + TB-4 Correr:`, `n8n_mcp.py — MCP Server local para controlar o n8n via Claude Code / Claude Desk`
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 5`** (2 nodes): `_activate_workflow()`, `_api_patch()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 6`** (2 nodes): `call_tool()`, `_dispatch()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `_api_get()` connect `Community 3` to `Community 2`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **What connects `create_workflows.py — Cria os workflows iniciais no n8n via API REST Correr: pyt`, `create_workflows_phase2.py — Workflows Fase 2: WorkGadget + FAT-2 + TB-4 Correr:`, `n8n_mcp.py — MCP Server local para controlar o n8n via Claude Code / Claude Desk` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._