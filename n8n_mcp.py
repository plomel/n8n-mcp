"""
n8n_mcp.py — MCP Server local para controlar o n8n via Claude Code / Claude Desktop
Permite criar, editar, accionar workflows e guardar logs no Obsidian Vault.

Instalar: pip install mcp httpx python-dotenv
Correr:   python n8n_mcp.py
Registar: ver CLAUDE.md deste projecto
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Carregar .env do mesmo directório
load_dotenv(Path(__file__).parent / ".env")

N8N_URL   = os.getenv("N8N_URL", "http://localhost:5678").rstrip("/")
N8N_KEY   = os.getenv("N8N_API_KEY", "")
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"C:\Users\Ryzen 7 5700g Gamer\Documents\Claude\Obsidian_Vault One"))

HEADERS = {
    "X-N8N-API-KEY": N8N_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# ── Servidor MCP ──────────────────────────────────────────
server = Server("n8n-controller")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # ── Gestão de Workflows ──────────────────────────
        Tool(
            name="list_workflows",
            description="Lista todos os workflows existentes no n8n com id, nome e estado (activo/inactivo).",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_workflow",
            description="Retorna a definição completa de um workflow (nós, ligações, configurações).",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "ID do workflow no n8n"}
                },
                "required": ["workflow_id"],
            },
        ),
        Tool(
            name="create_workflow",
            description=(
                "Cria um novo workflow no n8n. "
                "Passa 'name' (nome do workflow), 'nodes' (lista de nós) e 'connections' (dict de ligações). "
                "Retorna o id do workflow criado."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name":        {"type": "string", "description": "Nome do workflow"},
                    "nodes":       {"type": "array",  "description": "Lista de nós do workflow (formato n8n)"},
                    "connections": {"type": "object", "description": "Ligações entre nós (formato n8n)", "default": {}},
                    "active":      {"type": "boolean", "description": "Activar imediatamente?", "default": False},
                },
                "required": ["name", "nodes"],
            },
        ),
        Tool(
            name="update_workflow",
            description="Actualiza um workflow existente (nós, ligações ou nome).",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "ID do workflow"},
                    "name":        {"type": "string", "description": "Novo nome (opcional)"},
                    "nodes":       {"type": "array",  "description": "Lista de nós actualizada"},
                    "connections": {"type": "object", "description": "Ligações actualizadas"},
                },
                "required": ["workflow_id", "nodes"],
            },
        ),
        Tool(
            name="delete_workflow",
            description="Remove permanentemente um workflow do n8n.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "ID do workflow a remover"}
                },
                "required": ["workflow_id"],
            },
        ),
        Tool(
            name="activate_workflow",
            description="Activa ou desactiva um workflow (toggle).",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string",  "description": "ID do workflow"},
                    "active":      {"type": "boolean", "description": "True para activar, False para desactivar"},
                },
                "required": ["workflow_id", "active"],
            },
        ),
        # ── Execução ─────────────────────────────────────
        Tool(
            name="trigger_workflow",
            description=(
                "Acciona um workflow manualmente via webhook ou run directo. "
                "Passa dados opcionais no campo 'data'. Retorna execution_id."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "ID do workflow"},
                    "data":        {"type": "object", "description": "Dados de entrada (opcional)", "default": {}},
                },
                "required": ["workflow_id"],
            },
        ),
        Tool(
            name="get_execution",
            description="Retorna o estado e resultado de uma execução (finished, running, error).",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string", "description": "ID da execução"}
                },
                "required": ["execution_id"],
            },
        ),
        Tool(
            name="list_executions",
            description="Lista execuções recentes de um workflow com estado e timestamps.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string",  "description": "ID do workflow"},
                    "limit":       {"type": "integer", "description": "Número máximo de resultados", "default": 10},
                },
                "required": ["workflow_id"],
            },
        ),
        # ── Obsidian Vault ────────────────────────────────
        Tool(
            name="write_vault_log",
            description=(
                "Escreve um ficheiro markdown no Vault do Obsidian em Automation-Logs/. "
                "Usa para guardar resultados, estados e memória de execuções. "
                "O filename não deve ter extensão (adicionada automaticamente)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Nome do ficheiro sem extensão (ex: 'btc-monitor-2026-04-16')"},
                    "content":  {"type": "string", "description": "Conteúdo markdown do ficheiro"},
                },
                "required": ["filename", "content"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        result = await _dispatch(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def _dispatch(name: str, args: dict) -> Any:
    loop = asyncio.get_event_loop()

    # Gestão de Workflows
    if name == "list_workflows":
        return await loop.run_in_executor(None, _list_workflows)

    elif name == "get_workflow":
        return await loop.run_in_executor(None, _get_workflow, args["workflow_id"])

    elif name == "create_workflow":
        return await loop.run_in_executor(
            None, _create_workflow,
            args["name"],
            args["nodes"],
            args.get("connections", {}),
            args.get("active", False),
        )

    elif name == "update_workflow":
        return await loop.run_in_executor(
            None, _update_workflow,
            args["workflow_id"],
            args["nodes"],
            args.get("connections", {}),
            args.get("name"),
        )

    elif name == "delete_workflow":
        return await loop.run_in_executor(None, _delete_workflow, args["workflow_id"])

    elif name == "activate_workflow":
        return await loop.run_in_executor(None, _activate_workflow, args["workflow_id"], args["active"])

    # Execução
    elif name == "trigger_workflow":
        return await loop.run_in_executor(
            None, _trigger_workflow,
            args["workflow_id"],
            args.get("data", {}),
        )

    elif name == "get_execution":
        return await loop.run_in_executor(None, _get_execution, args["execution_id"])

    elif name == "list_executions":
        return await loop.run_in_executor(
            None, _list_executions,
            args["workflow_id"],
            args.get("limit", 10),
        )

    # Obsidian
    elif name == "write_vault_log":
        return await loop.run_in_executor(
            None, _write_vault_log,
            args["filename"],
            args["content"],
        )

    raise ValueError(f"Ferramenta desconhecida: {name}")


# ── Implementações ─────────────────────────────────────────

def _api_get(path: str) -> dict:
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{N8N_URL}/api/v1{path}", headers=HEADERS)
        r.raise_for_status()
        return r.json()


def _api_post(path: str, body: dict) -> dict:
    with httpx.Client(timeout=30) as client:
        r = client.post(f"{N8N_URL}/api/v1{path}", headers=HEADERS, json=body)
        r.raise_for_status()
        return r.json()


def _api_put(path: str, body: dict) -> dict:
    with httpx.Client(timeout=30) as client:
        r = client.put(f"{N8N_URL}/api/v1{path}", headers=HEADERS, json=body)
        r.raise_for_status()
        return r.json()


def _api_delete(path: str) -> dict:
    with httpx.Client(timeout=30) as client:
        r = client.delete(f"{N8N_URL}/api/v1{path}", headers=HEADERS)
        r.raise_for_status()
        return {"deleted": True}


def _api_patch(path: str, body: dict) -> dict:
    with httpx.Client(timeout=30) as client:
        r = client.patch(f"{N8N_URL}/api/v1{path}", headers=HEADERS, json=body)
        r.raise_for_status()
        return r.json()


# Workflows

def _list_workflows() -> dict:
    data = _api_get("/workflows")
    workflows = data.get("data", data) if isinstance(data, dict) else data
    return {
        "count": len(workflows),
        "workflows": [
            {"id": w.get("id"), "name": w.get("name"), "active": w.get("active", False)}
            for w in workflows
        ],
    }


def _get_workflow(workflow_id: str) -> dict:
    return _api_get(f"/workflows/{workflow_id}")


def _create_workflow(name: str, nodes: list, connections: dict, active: bool) -> dict:
    body = {
        "name": name,
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1"},
        "active": active,
    }
    result = _api_post("/workflows", body)
    return {
        "status": "criado",
        "workflow_id": result.get("id"),
        "name": result.get("name"),
        "active": result.get("active"),
    }


def _update_workflow(workflow_id: str, nodes: list, connections: dict, name: str | None) -> dict:
    existing = _api_get(f"/workflows/{workflow_id}")
    body = {
        "name": name or existing.get("name"),
        "nodes": nodes,
        "connections": connections,
        "settings": existing.get("settings", {"executionOrder": "v1"}),
    }
    result = _api_put(f"/workflows/{workflow_id}", body)
    return {
        "status": "actualizado",
        "workflow_id": result.get("id"),
        "name": result.get("name"),
    }


def _delete_workflow(workflow_id: str) -> dict:
    _api_delete(f"/workflows/{workflow_id}")
    return {"status": "removido", "workflow_id": workflow_id}


def _activate_workflow(workflow_id: str, active: bool) -> dict:
    if active:
        result = _api_patch(f"/workflows/{workflow_id}/activate", {})
    else:
        result = _api_patch(f"/workflows/{workflow_id}/deactivate", {})
    return {
        "status": "activado" if active else "desactivado",
        "workflow_id": workflow_id,
    }


# Execuções

def _trigger_workflow(workflow_id: str, data: dict) -> dict:
    result = _api_post(f"/workflows/{workflow_id}/run", {"runData": data})
    return {
        "status": "disparado",
        "execution_id": result.get("data", {}).get("executionId") or result.get("executionId"),
        "workflow_id": workflow_id,
    }


def _get_execution(execution_id: str) -> dict:
    data = _api_get(f"/executions/{execution_id}")
    return {
        "execution_id": execution_id,
        "status": data.get("status"),
        "finished": data.get("finished"),
        "started_at": data.get("startedAt"),
        "stopped_at": data.get("stoppedAt"),
        "error": data.get("data", {}).get("resultData", {}).get("error"),
    }


def _list_executions(workflow_id: str, limit: int) -> dict:
    data = _api_get(f"/executions?workflowId={workflow_id}&limit={min(limit, 20)}")
    executions = data.get("data", data) if isinstance(data, dict) else data
    return {
        "workflow_id": workflow_id,
        "count": len(executions),
        "executions": [
            {
                "id": e.get("id"),
                "status": e.get("status"),
                "finished": e.get("finished"),
                "started_at": e.get("startedAt"),
            }
            for e in executions
        ],
    }


# Obsidian

def _write_vault_log(filename: str, content: str) -> dict:
    log_dir = VAULT_PATH / "Automation-Logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    safe_name = filename.replace("/", "-").replace("\\", "-")
    if not safe_name.endswith(".md"):
        safe_name += ".md"

    filepath = log_dir / safe_name
    filepath.write_text(content, encoding="utf-8")

    return {
        "status": "guardado",
        "path": str(filepath),
        "filename": safe_name,
        "timestamp": datetime.now().isoformat(),
    }


# ── Arranque ──────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if not N8N_KEY:
        print("ERRO: Define N8N_API_KEY no ficheiro .env", file=sys.stderr)
        print(f"  Ficheiro esperado: {Path(__file__).parent / '.env'}", file=sys.stderr)
        sys.exit(1)

    print(f"✅ n8n MCP Server a arrancar... (n8n: {N8N_URL})", file=sys.stderr)

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(main())
