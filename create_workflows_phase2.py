"""
create_workflows_phase2.py — Workflows Fase 2: WorkGadget + FAT-2 + TB-4
Correr: python create_workflows_phase2.py
"""

import json
import httpx
import uuid

N8N_URL = "http://localhost:5678"
N8N_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwYzRmNjk2ZC00NzBlLTRjMTMtYjE4NC1hYjA3MmNmNGQ2YjAiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiYzA5N2ZkZDktMTlhZC00ZTM0LWIzOTEtYzU2Y2IzZGUzNGJkIiwiaWF0IjoxNzc2MzAzMTEyfQ.LdaFfr5SnE5wpEIgiLfICpzGtpMX6jTGJDSsmz437XE"
HEADERS = {
    "X-N8N-API-KEY": N8N_KEY,
    "Content-Type": "application/json",
}


def uid():
    return str(uuid.uuid4())


def create_workflow(workflow: dict) -> dict:
    r = httpx.post(f"{N8N_URL}/api/v1/workflows", headers=HEADERS, json=workflow, timeout=30)
    r.raise_for_status()
    data = r.json()
    wf_id = data["id"]
    httpx.patch(f"{N8N_URL}/api/v1/workflows/{wf_id}/activate", headers=HEADERS, timeout=30)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# WG-1: Product Discovery Pipeline (diário às 09:00)
# CJDropshipping trending → Groq score → Notion → Gmail se score ≥ 8
# ─────────────────────────────────────────────────────────────────────────────
def workflow_wg1_product_discovery():
    n_sched   = uid()
    n_cj      = uid()
    n_split   = uid()
    n_groq    = uid()
    n_code    = uid()
    n_if      = uid()
    n_notion  = uid()
    n_gmail   = uid()

    return {
        "name": "[WG] Product Discovery — Diário 09h",
        "nodes": [
            {
                "id": n_sched,
                "name": "Daily 09:00",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 300],
                "parameters": {
                    "rule": {"interval": [{"field": "cronExpression", "expression": "0 9 * * *"}]}
                },
            },
            {
                "id": n_cj,
                "name": "CJ Trending Products",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [220, 300],
                "parameters": {
                    "method": "GET",
                    "url": "https://developers.cjdropshipping.com/api2.0/v1/product/list",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "CJ-Access-Token", "value": "={{ $vars.CJ_ACCESS_TOKEN }}"}
                        ]
                    },
                    "sendQuery": True,
                    "queryParameters": {
                        "parameters": [
                            {"name": "categoryKeyword", "value": "smart home"},
                            {"name": "pageNum", "value": "1"},
                            {"name": "pageSize", "value": "10"},
                            {"name": "sortField", "value": "quantity"},
                            {"name": "sortType", "value": "DESC"},
                        ]
                    },
                    "options": {},
                },
            },
            {
                "id": n_split,
                "name": "Split Products",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [460, 300],
                "parameters": {
                    "mode": "runOnceForAllItems",
                    "jsCode": """
const response = $input.first().json;
const products = response.data?.list || response.result?.list || [];

// Limitar a 5 produtos por run para não sobrecarregar
return products.slice(0, 5).map(p => ({
  json: {
    pid: p.pid || p.productId || '',
    name: p.productNameEn || p.productName || 'Sem nome',
    price: parseFloat(p.sellPrice || p.suggestSellingPrice || 0),
    category: p.categoryName || '',
    imageUrl: p.productImage || p.mainImage || '',
    salesVolume: parseInt(p.quantity || 0),
    supplierCountry: p.countryCode || 'CN',
  }
}));
""",
                },
            },
            {
                "id": n_groq,
                "name": "Groq Score Product",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [700, 300],
                "parameters": {
                    "method": "POST",
                    "url": "https://api.groq.com/openai/v1/chat/completions",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "Authorization", "value": "=Bearer {{ $vars.GROQ_API_KEY }}"},
                            {"name": "Content-Type", "value": "application/json"},
                        ]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"model\": \"llama-3.3-70b-versatile\",\n  \"messages\": [\n    {\n      \"role\": \"system\",\n      \"content\": \"És um especialista em dropshipping para o mercado português. Avalia produtos para uma loja Shopify focada em gadgets smart home e home office abaixo de €20. Responde APENAS com JSON válido.\"\n    },\n    {\n      \"role\": \"user\",\n      \"content\": \"Avalia este produto para o mercado PT:\\nNome: {{ $json.name }}\\nPreço fornecedor: ${{ $json.price }}\\nCategoria: {{ $json.category }}\\nVendas: {{ $json.salesVolume }}\\n\\nResponde com JSON: {\\\"score\\\": 1-10, \\\"reason\\\": \\\"motivo breve\\\", \\\"priceRecommendedEUR\\\": 0.00, \\\"targetAudience\\\": \\\"quem compra\\\"}\"\n    }\n  ],\n  \"temperature\": 0.3,\n  \"max_tokens\": 200\n}",
                    "options": {},
                },
            },
            {
                "id": n_code,
                "name": "Parse Score",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [940, 300],
                "parameters": {
                    "jsCode": """
const product = $('Split Products').item.json;
const groqResponse = $input.item.json;

let evaluation = {};
try {
  const content = groqResponse.choices[0].message.content;
  // Extrair JSON da resposta
  const jsonMatch = content.match(/\\{[\\s\\S]*\\}/);
  evaluation = jsonMatch ? JSON.parse(jsonMatch[0]) : {};
} catch(e) {
  evaluation = { score: 5, reason: 'Erro ao parsear', priceRecommendedEUR: product.price * 1.1, targetAudience: 'Geral' };
}

return {
  json: {
    ...product,
    score: evaluation.score || 5,
    reason: evaluation.reason || '',
    priceRecommendedEUR: evaluation.priceRecommendedEUR || (product.price * 1.1),
    targetAudience: evaluation.targetAudience || '',
    highScore: (evaluation.score || 5) >= 8,
  }
};
""",
                },
            },
            {
                "id": n_if,
                "name": "Score >= 8?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "position": [1180, 300],
                "parameters": {
                    "conditions": {
                        "conditions": [
                            {
                                "leftValue": "={{ $json.highScore }}",
                                "rightValue": True,
                                "operator": {"type": "boolean", "operation": "equals"},
                            }
                        ],
                        "combinator": "and",
                    }
                },
            },
            {
                "id": n_notion,
                "name": "Add to Notion",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [1420, 200],
                "parameters": {
                    "method": "POST",
                    "url": "https://api.notion.com/v1/pages",
                    "authentication": "predefinedCredentialType",
                    "nodeCredentialType": "notionApi",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [{"name": "Notion-Version", "value": "2022-06-28"}]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"parent\": { \"database_id\": \"SUBSTITUIR_PELO_ID_DATABASE_PRODUTOS\" },\n  \"properties\": {\n    \"Name\": { \"title\": [{ \"text\": { \"content\": \"{{ $json.name }}\" } }] },\n    \"Score\": { \"number\": {{ $json.score }} },\n    \"Preço Fornecedor\": { \"number\": {{ $json.price }} },\n    \"Preço Recomendado EUR\": { \"number\": {{ $json.priceRecommendedEUR }} },\n    \"Categoria\": { \"select\": { \"name\": \"{{ $json.category }}\" } },\n    \"Status\": { \"select\": { \"name\": \"Em análise\" } },\n    \"Notas\": { \"rich_text\": [{ \"text\": { \"content\": \"{{ $json.reason }}\" } }] },\n    \"Público-Alvo\": { \"rich_text\": [{ \"text\": { \"content\": \"{{ $json.targetAudience }}\" } }] }\n  }\n}",
                    "options": {},
                },
            },
            {
                "id": n_gmail,
                "name": "Alert High Score",
                "type": "n8n-nodes-base.gmail",
                "typeVersion": 2.1,
                "position": [1420, 400],
                "parameters": {
                    "operation": "send",
                    "sendTo": "pablomaciel2003.pm@gmail.com",
                    "subject": "=🛒 Produto score {{ $json.score }}/10 — {{ $json.name }}",
                    "emailType": "text",
                    "message": "=Novo produto de alta pontuação encontrado!\n\n📦 {{ $json.name }}\n⭐ Score: {{ $json.score }}/10\n💰 Preço fornecedor: ${{ $json.price }}\n💶 Preço recomendado PT: €{{ $json.priceRecommendedEUR.toFixed(2) }}\n🎯 Público: {{ $json.targetAudience }}\n📝 Motivo: {{ $json.reason }}\n\nAdicionar ao Notion → Aprovar → Upload automático para Shopify.",
                    "options": {},
                },
                "credentials": {"gmailOAuth2": {"id": "gmail-credential", "name": "Gmail OAuth2"}},
            },
        ],
        "connections": {
            "Daily 09:00":         {"main": [[{"node": "CJ Trending Products", "type": "main", "index": 0}]]},
            "CJ Trending Products": {"main": [[{"node": "Split Products",       "type": "main", "index": 0}]]},
            "Split Products":       {"main": [[{"node": "Groq Score Product",   "type": "main", "index": 0}]]},
            "Groq Score Product":   {"main": [[{"node": "Parse Score",          "type": "main", "index": 0}]]},
            "Parse Score":          {"main": [[{"node": "Score >= 8?",          "type": "main", "index": 0}]]},
            "Score >= 8?": {
                "main": [
                    [{"node": "Add to Notion",    "type": "main", "index": 0},
                     {"node": "Alert High Score", "type": "main", "index": 0}],
                    [{"node": "Add to Notion",    "type": "main", "index": 0}]  # score baixo → notion sem email
                ]
            },
        },
        "settings": {"executionOrder": "v1"},
    }


# ─────────────────────────────────────────────────────────────────────────────
# WG-2: Product Upload to Shopify (webhook — acionado quando status Notion = "Aprovado")
# ─────────────────────────────────────────────────────────────────────────────
def workflow_wg2_product_upload():
    n_webhook = uid()
    n_groq    = uid()
    n_shopify = uid()
    n_notion  = uid()
    n_gmail   = uid()

    return {
        "name": "[WG] Product Upload → Shopify",
        "nodes": [
            {
                "id": n_webhook,
                "name": "Webhook — Product Approved",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [0, 300],
                "parameters": {
                    "httpMethod": "POST",
                    "path": "product-approved",
                    "responseMode": "onReceived",
                    "options": {},
                },
                "webhookId": "product-approved-wg",
            },
            {
                "id": n_groq,
                "name": "Groq — Gerar Descrição PT",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [220, 300],
                "parameters": {
                    "method": "POST",
                    "url": "https://api.groq.com/openai/v1/chat/completions",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "Authorization", "value": "=Bearer {{ $vars.GROQ_API_KEY }}"},
                            {"name": "Content-Type", "value": "application/json"},
                        ]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"model\": \"llama-3.3-70b-versatile\",\n  \"messages\": [\n    {\n      \"role\": \"system\",\n      \"content\": \"Escreves descrições de produtos Shopify em português de Portugal. Tom: direto, prático, sem exageros. Máximo 120 palavras. Inclui 3 bullet points com benefícios principais.\"\n    },\n    {\n      \"role\": \"user\",\n      \"content\": \"Produto: {{ $json.body.name }}\\nCategoria: {{ $json.body.category }}\\nPreço: €{{ $json.body.priceEUR }}\\nPúblico: {{ $json.body.targetAudience }}\\n\\nEscreve a descrição.\"\n    }\n  ],\n  \"temperature\": 0.7,\n  \"max_tokens\": 300\n}",
                    "options": {},
                },
            },
            {
                "id": n_shopify,
                "name": "Create Shopify Product",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [460, 300],
                "parameters": {
                    "method": "POST",
                    "url": "=https://{{ $vars.SHOPIFY_STORE }}.myshopify.com/admin/api/2024-01/products.json",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "X-Shopify-Access-Token", "value": "={{ $vars.SHOPIFY_ACCESS_TOKEN }}"},
                            {"name": "Content-Type", "value": "application/json"},
                        ]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"product\": {\n    \"title\": \"{{ $('Webhook — Product Approved').first().json.body.name }}\",\n    \"body_html\": \"{{ $json.choices[0].message.content }}\",\n    \"vendor\": \"WorkGadget\",\n    \"product_type\": \"{{ $('Webhook — Product Approved').first().json.body.category }}\",\n    \"status\": \"draft\",\n    \"variants\": [{\n      \"price\": \"{{ $('Webhook — Product Approved').first().json.body.priceEUR }}\",\n      \"inventory_management\": \"shopify\",\n      \"inventory_quantity\": 999\n    }],\n    \"tags\": \"dropshipping, cj, {{ $('Webhook — Product Approved').first().json.body.category }}\"\n  }\n}",
                    "options": {},
                },
            },
            {
                "id": n_notion,
                "name": "Update Notion Status",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [700, 200],
                "parameters": {
                    "method": "PATCH",
                    "url": "=https://api.notion.com/v1/pages/{{ $('Webhook — Product Approved').first().json.body.notionPageId }}",
                    "authentication": "predefinedCredentialType",
                    "nodeCredentialType": "notionApi",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [{"name": "Notion-Version", "value": "2022-06-28"}]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"properties\": {\n    \"Status\": { \"select\": { \"name\": \"Publicado\" } },\n    \"Shopify ID\": { \"rich_text\": [{ \"text\": { \"content\": \"{{ $json.product.id }}\" } }] }\n  }\n}",
                    "options": {},
                },
            },
            {
                "id": n_gmail,
                "name": "Confirm Upload",
                "type": "n8n-nodes-base.gmail",
                "typeVersion": 2.1,
                "position": [700, 400],
                "parameters": {
                    "operation": "send",
                    "sendTo": "pablomaciel2003.pm@gmail.com",
                    "subject": "=✅ Produto publicado na Shopify — {{ $('Webhook — Product Approved').first().json.body.name }}",
                    "emailType": "text",
                    "message": "=Produto adicionado como rascunho na Shopify!\n\n📦 {{ $('Webhook — Product Approved').first().json.body.name }}\n🆔 Shopify ID: {{ $('Create Shopify Product').first().json.product.id }}\n💶 Preço: €{{ $('Webhook — Product Approved').first().json.body.priceEUR }}\n\nAceder: https://{{ $vars.SHOPIFY_STORE }}.myshopify.com/admin/products/{{ $('Create Shopify Product').first().json.product.id }}",
                    "options": {},
                },
                "credentials": {"gmailOAuth2": {"id": "gmail-credential", "name": "Gmail OAuth2"}},
            },
        ],
        "connections": {
            "Webhook — Product Approved": {"main": [[{"node": "Groq — Gerar Descrição PT", "type": "main", "index": 0}]]},
            "Groq — Gerar Descrição PT":  {"main": [[{"node": "Create Shopify Product",    "type": "main", "index": 0}]]},
            "Create Shopify Product":     {"main": [[{"node": "Update Notion Status",       "type": "main", "index": 0},
                                                     {"node": "Confirm Upload",             "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


# ─────────────────────────────────────────────────────────────────────────────
# WG-3: Competitor Price Monitor (cada 6h)
# Playwright scrape → comparar com Shopify → Notion intelligence
# ─────────────────────────────────────────────────────────────────────────────
def workflow_wg3_price_monitor():
    n_sched  = uid()
    n_shop1  = uid()
    n_shop2  = uid()
    n_code   = uid()
    n_groq   = uid()
    n_notion = uid()
    n_if     = uid()
    n_gmail  = uid()

    return {
        "name": "[WG] Competitor Price Monitor — 6h",
        "nodes": [
            {
                "id": n_sched,
                "name": "Every 6h",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 300],
                "parameters": {
                    "rule": {"interval": [{"field": "hours", "hoursInterval": 6}]}
                },
            },
            {
                "id": n_shop1,
                "name": "Scrape Aliexpress",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [220, 200],
                "parameters": {
                    "method": "GET",
                    "url": "https://api.scraperapi.com/",
                    "sendQuery": True,
                    "queryParameters": {
                        "parameters": [
                            {"name": "api_key", "value": "={{ $vars.SCRAPER_API_KEY }}"},
                            {"name": "url", "value": "https://pt.aliexpress.com/category/201000048/smart-home-gadgets.html"},
                        ]
                    },
                    "options": {},
                },
                "notes": "Usa ScraperAPI (alternativa: Apify). Configurar SCRAPER_API_KEY em n8n Variables.",
            },
            {
                "id": n_shop2,
                "name": "GET Our Shopify Prices",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [220, 400],
                "parameters": {
                    "method": "GET",
                    "url": "=https://{{ $vars.SHOPIFY_STORE }}.myshopify.com/admin/api/2024-01/products.json?limit=10",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "X-Shopify-Access-Token", "value": "={{ $vars.SHOPIFY_ACCESS_TOKEN }}"}
                        ]
                    },
                    "options": {},
                },
            },
            {
                "id": n_code,
                "name": "Analyze Prices",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [460, 300],
                "parameters": {
                    "mode": "runOnceForAllItems",
                    "jsCode": """
// Análise básica de preços
// ScraperAPI devolve HTML — parsing simplificado aqui
const ourProducts = $('GET Our Shopify Prices').first().json?.products || [];
const now = new Date().toISOString();

const summary = ourProducts.map(p => ({
  name: p.title,
  ourPrice: parseFloat(p.variants?.[0]?.price || 0),
  shopifyId: p.id,
}));

const avgPrice = summary.length > 0
  ? summary.reduce((s, p) => s + p.ourPrice, 0) / summary.length
  : 0;

return [{
  json: {
    timestamp: now,
    productsAnalyzed: summary.length,
    avgOurPrice: avgPrice,
    products: summary,
    needsAlert: false, // Será avaliado pelo Groq abaixo
    summary: JSON.stringify(summary.slice(0, 5))
  }
}];
""",
                },
            },
            {
                "id": n_groq,
                "name": "Groq — Analyze Competitiveness",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [700, 300],
                "parameters": {
                    "method": "POST",
                    "url": "https://api.groq.com/openai/v1/chat/completions",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "Authorization", "value": "=Bearer {{ $vars.GROQ_API_KEY }}"},
                            {"name": "Content-Type", "value": "application/json"},
                        ]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"model\": \"llama-3.1-8b-instant\",\n  \"messages\": [\n    {\n      \"role\": \"system\",\n      \"content\": \"Analisas competitividade de preços para dropshipping em Portugal. Responde apenas com JSON.\"\n    },\n    {\n      \"role\": \"user\",\n      \"content\": \"Produtos na nossa loja: {{ $json.summary }}\\nPreço médio: €{{ $json.avgOurPrice.toFixed(2) }}\\n\\nComentário breve sobre competitividade e se precisamos ajustar preços. JSON: {\\\"competitive\\\": true/false, \\\"recommendation\\\": \\\"texto\\\", \\\"urgency\\\": \\\"low/medium/high\\\"}\"\n    }\n  ],\n  \"temperature\": 0.3,\n  \"max_tokens\": 150\n}",
                    "options": {},
                },
            },
            {
                "id": n_notion,
                "name": "Update Price Intelligence",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [940, 200],
                "parameters": {
                    "method": "POST",
                    "url": "https://api.notion.com/v1/pages",
                    "authentication": "predefinedCredentialType",
                    "nodeCredentialType": "notionApi",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [{"name": "Notion-Version", "value": "2022-06-28"}]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"parent\": { \"database_id\": \"SUBSTITUIR_PELO_ID_DATABASE_PRICE_INTELLIGENCE\" },\n  \"properties\": {\n    \"Name\": { \"title\": [{ \"text\": { \"content\": \"Price Check {{ $('Analyze Prices').first().json.timestamp }}\" } }] },\n    \"Avg Price EUR\": { \"number\": {{ $('Analyze Prices').first().json.avgOurPrice }} },\n    \"Produtos Analisados\": { \"number\": {{ $('Analyze Prices').first().json.productsAnalyzed }} },\n    \"Data\": { \"date\": { \"start\": \"{{ $('Analyze Prices').first().json.timestamp }}\" } }\n  }\n}",
                    "options": {},
                },
            },
            {
                "id": n_if,
                "name": "Urgency High?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "position": [940, 400],
                "parameters": {
                    "conditions": {
                        "conditions": [
                            {
                                "leftValue": "={{ JSON.parse($json.choices[0].message.content.match(/\\{[\\s\\S]*\\}/)[0]).urgency }}",
                                "rightValue": "high",
                                "operator": {"type": "string", "operation": "equals"},
                            }
                        ],
                        "combinator": "and",
                    }
                },
            },
            {
                "id": n_gmail,
                "name": "Price Alert Email",
                "type": "n8n-nodes-base.gmail",
                "typeVersion": 2.1,
                "position": [1180, 400],
                "parameters": {
                    "operation": "send",
                    "sendTo": "pablomaciel2003.pm@gmail.com",
                    "subject": "⚠️ WorkGadget — Alerta de Preços",
                    "emailType": "text",
                    "message": "=Análise de competitividade detectou urgência alta!\n\n{{ $json.choices[0].message.content }}\n\nPreço médio atual: €{{ $('Analyze Prices').first().json.avgOurPrice.toFixed(2) }}\nProdutos: {{ $('Analyze Prices').first().json.productsAnalyzed }}",
                    "options": {},
                },
                "credentials": {"gmailOAuth2": {"id": "gmail-credential", "name": "Gmail OAuth2"}},
            },
        ],
        "connections": {
            "Every 6h":                      {"main": [[{"node": "Scrape Aliexpress",             "type": "main", "index": 0},
                                                        {"node": "GET Our Shopify Prices",         "type": "main", "index": 0}]]},
            "Scrape Aliexpress":             {"main": [[{"node": "Analyze Prices",                 "type": "main", "index": 0}]]},
            "GET Our Shopify Prices":        {"main": [[{"node": "Analyze Prices",                 "type": "main", "index": 0}]]},
            "Analyze Prices":               {"main": [[{"node": "Groq — Analyze Competitiveness", "type": "main", "index": 0}]]},
            "Groq — Analyze Competitiveness": {"main": [[{"node": "Update Price Intelligence",    "type": "main", "index": 0},
                                                          {"node": "Urgency High?",               "type": "main", "index": 0}]]},
            "Urgency High?": {"main": [[{"node": "Price Alert Email", "type": "main", "index": 0}], []]},
        },
        "settings": {"executionOrder": "v1"},
    }


# ─────────────────────────────────────────────────────────────────────────────
# WG-4: Weekly Sales Report (domingo às 20:00)
# Shopify sales → Groq insights → Google Drive doc → Gmail → trigger WG-1
# ─────────────────────────────────────────────────────────────────────────────
def workflow_wg4_weekly_report():
    n_sched  = uid()
    n_sales  = uid()
    n_orders = uid()
    n_groq   = uid()
    n_gmail  = uid()

    return {
        "name": "[WG] Weekly Sales Report — Domingo 20h",
        "nodes": [
            {
                "id": n_sched,
                "name": "Sunday 20:00",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 300],
                "parameters": {
                    "rule": {"interval": [{"field": "cronExpression", "expression": "0 20 * * 0"}]}
                },
            },
            {
                "id": n_sales,
                "name": "GET Shopify Orders",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [220, 200],
                "parameters": {
                    "method": "GET",
                    "url": "=https://{{ $vars.SHOPIFY_STORE }}.myshopify.com/admin/api/2024-01/orders.json",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "X-Shopify-Access-Token", "value": "={{ $vars.SHOPIFY_ACCESS_TOKEN }}"}
                        ]
                    },
                    "sendQuery": True,
                    "queryParameters": {
                        "parameters": [
                            {"name": "status", "value": "any"},
                            {"name": "limit", "value": "50"},
                            {"name": "created_at_min", "value": "={{ new Date(Date.now() - 7*24*60*60*1000).toISOString() }}"},
                        ]
                    },
                    "options": {},
                },
            },
            {
                "id": n_orders,
                "name": "Calculate Weekly Stats",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [220, 400],
                "parameters": {
                    "jsCode": """
const ordersData = $('GET Shopify Orders').first().json;
const orders = ordersData.orders || [];
const weekStart = new Date(Date.now() - 7*24*60*60*1000).toLocaleDateString('pt-PT');
const weekEnd   = new Date().toLocaleDateString('pt-PT');

const totalRevenue = orders.reduce((s, o) => s + parseFloat(o.total_price || 0), 0);
const totalOrders  = orders.length;
const avgOrderVal  = totalOrders > 0 ? totalRevenue / totalOrders : 0;

// Top produtos
const productCounts = {};
orders.forEach(o => {
  (o.line_items || []).forEach(item => {
    productCounts[item.title] = (productCounts[item.title] || 0) + item.quantity;
  });
});
const topProducts = Object.entries(productCounts)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 3)
  .map(([name, qty]) => `  • ${name}: ${qty} unidades`);

const statsText = `Semana: ${weekStart} – ${weekEnd}
Total de encomendas: ${totalOrders}
Receita total: €${totalRevenue.toFixed(2)}
Valor médio por encomenda: €${avgOrderVal.toFixed(2)}
Top produtos:\n${topProducts.join('\n') || '  (sem dados)'}`;

return [{ json: { totalRevenue, totalOrders, avgOrderVal, statsText, weekStart, weekEnd, topProductsJson: JSON.stringify(productCounts) } }];
""",
                },
            },
            {
                "id": n_groq,
                "name": "Groq — Weekly Insights",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [460, 300],
                "parameters": {
                    "method": "POST",
                    "url": "https://api.groq.com/openai/v1/chat/completions",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "Authorization", "value": "=Bearer {{ $vars.GROQ_API_KEY }}"},
                            {"name": "Content-Type", "value": "application/json"},
                        ]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"model\": \"llama-3.3-70b-versatile\",\n  \"messages\": [\n    {\n      \"role\": \"system\",\n      \"content\": \"Analistas de e-commerce para dropshipping em Portugal. Dás insights práticos e recomendações concretas. Responde em português de Portugal.\"\n    },\n    {\n      \"role\": \"user\",\n      \"content\": \"Dados da semana na loja WorkGadget:\\n{{ $json.statsText }}\\n\\nDá 3 insights acionáveis e 2 recomendações para a próxima semana. Formato: 3 bullet points de insight + 2 de recomendação.\"\n    }\n  ],\n  \"temperature\": 0.5,\n  \"max_tokens\": 400\n}",
                    "options": {},
                },
            },
            {
                "id": n_gmail,
                "name": "Send Weekly Report",
                "type": "n8n-nodes-base.gmail",
                "typeVersion": 2.1,
                "position": [700, 300],
                "parameters": {
                    "operation": "send",
                    "sendTo": "pablomaciel2003.pm@gmail.com",
                    "subject": "=📊 WorkGadget — Relatório Semanal {{ $('Calculate Weekly Stats').first().json.weekStart }} a {{ $('Calculate Weekly Stats').first().json.weekEnd }}",
                    "emailType": "text",
                    "message": "=📊 RELATÓRIO SEMANAL — WorkGadget\n════════════════════════════\n\n{{ $('Calculate Weekly Stats').first().json.statsText }}\n\n────────────────────────────\n💡 ANÁLISE AI (Groq)\n────────────────────────────\n{{ $json.choices[0].message.content }}\n\n════════════════════════════\nGerado automaticamente por n8n · WorkGadget Automation",
                    "options": {},
                },
                "credentials": {"gmailOAuth2": {"id": "gmail-credential", "name": "Gmail OAuth2"}},
            },
        ],
        "connections": {
            "Sunday 20:00":               {"main": [[{"node": "GET Shopify Orders",       "type": "main", "index": 0},
                                                     {"node": "Calculate Weekly Stats",   "type": "main", "index": 0}]]},
            "GET Shopify Orders":         {"main": [[{"node": "Calculate Weekly Stats",   "type": "main", "index": 0}]]},
            "Calculate Weekly Stats":     {"main": [[{"node": "Groq — Weekly Insights",   "type": "main", "index": 0}]]},
            "Groq — Weekly Insights":    {"main": [[{"node": "Send Weekly Report",        "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


# ─────────────────────────────────────────────────────────────────────────────
# FAT-2: Monthly Audit (1º de cada mês às 09:00)
# Notion faturas → Groq cross-reference → Gmail relatório Tiago
# ─────────────────────────────────────────────────────────────────────────────
def workflow_fat2_monthly_audit():
    n_sched  = uid()
    n_notion = uid()
    n_groq   = uid()
    n_gmail  = uid()
    n_update = uid()

    return {
        "name": "[FAT] Monthly Audit — 1º do Mês",
        "nodes": [
            {
                "id": n_sched,
                "name": "1st of Month 09:00",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 300],
                "parameters": {
                    "rule": {"interval": [{"field": "cronExpression", "expression": "0 9 1 * *"}]}
                },
            },
            {
                "id": n_notion,
                "name": "GET Faturas do Mês",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [220, 300],
                "parameters": {
                    "method": "POST",
                    "url": "=https://api.notion.com/v1/databases/SUBSTITUIR_PELO_ID_DATABASE_FATURAS/query",
                    "authentication": "predefinedCredentialType",
                    "nodeCredentialType": "notionApi",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [{"name": "Notion-Version", "value": "2022-06-28"}]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"filter\": {\n    \"property\": \"Mês\",\n    \"rich_text\": {\n      \"equals\": \"{{ new Date(Date.now() - 30*24*60*60*1000).toISOString().slice(0,7) }}\"\n    }\n  }\n}",
                    "options": {},
                },
            },
            {
                "id": n_groq,
                "name": "Groq — Audit Analysis",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [460, 300],
                "parameters": {
                    "method": "POST",
                    "url": "https://api.groq.com/openai/v1/chat/completions",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "Authorization", "value": "=Bearer {{ $vars.GROQ_API_KEY }}"},
                            {"name": "Content-Type", "value": "application/json"},
                        ]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"model\": \"llama-3.3-70b-versatile\",\n  \"messages\": [\n    {\n      \"role\": \"system\",\n      \"content\": \"Fazes auditoria de faturas para uma empresa de restauração portuguesa (Rosa dos Leitões). Identifica duplicados, anomalias, faturas em falta. Responde em português de Portugal.\"\n    },\n    {\n      \"role\": \"user\",\n      \"content\": \"Faturas do mês anterior:\\n{{ JSON.stringify($json.results?.slice(0, 20).map(p => ({ remetente: p.properties?.Remetente?.rich_text?.[0]?.text?.content, valor: p.properties?.Valor?.number, data: p.properties?.Data?.date?.start, status: p.properties?.Status?.select?.name }))) }}\\n\\nGera relatório de auditoria: total faturas, valor total, suspeitos de duplicado, anomalias, recomendações.\"\n    }\n  ],\n  \"temperature\": 0.2,\n  \"max_tokens\": 600\n}",
                    "options": {},
                },
            },
            {
                "id": n_gmail,
                "name": "Send Audit Report",
                "type": "n8n-nodes-base.gmail",
                "typeVersion": 2.1,
                "position": [700, 200],
                "parameters": {
                    "operation": "send",
                    "sendTo": "pablomaciel2003.pm@gmail.com",
                    "subject": "=📋 Auditoria Faturas — {{ new Date(Date.now() - 30*24*60*60*1000).toISOString().slice(0,7) }}",
                    "emailType": "text",
                    "message": "=AUDITORIA MENSAL — Rosa dos Leitões\n{{ new Date(Date.now() - 30*24*60*60*1000).toISOString().slice(0,7) }}\n════════════════════════════════\n\n{{ $json.choices[0].message.content }}\n\n════════════════════════════════\nGerado automaticamente por n8n",
                    "options": {},
                },
                "credentials": {"gmailOAuth2": {"id": "gmail-credential", "name": "Gmail OAuth2"}},
            },
            {
                "id": n_update,
                "name": "Mark Month Audited",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [700, 400],
                "parameters": {
                    "method": "POST",
                    "url": "https://api.notion.com/v1/pages",
                    "authentication": "predefinedCredentialType",
                    "nodeCredentialType": "notionApi",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [{"name": "Notion-Version", "value": "2022-06-28"}]
                    },
                    "sendBody": True,
                    "contentType": "json",
                    "body": "={\n  \"parent\": { \"database_id\": \"SUBSTITUIR_PELO_ID_DATABASE_AUDIT_LOG\" },\n  \"properties\": {\n    \"Name\": { \"title\": [{ \"text\": { \"content\": \"Auditoria {{ new Date(Date.now() - 30*24*60*60*1000).toISOString().slice(0,7) }}\" } }] },\n    \"Status\": { \"select\": { \"name\": \"Auditado\" } },\n    \"Data\": { \"date\": { \"start\": \"{{ new Date().toISOString() }}\" } }\n  }\n}",
                    "options": {},
                },
            },
        ],
        "connections": {
            "1st of Month 09:00": {"main": [[{"node": "GET Faturas do Mês", "type": "main", "index": 0}]]},
            "GET Faturas do Mês":  {"main": [[{"node": "Groq — Audit Analysis", "type": "main", "index": 0}]]},
            "Groq — Audit Analysis": {"main": [[{"node": "Send Audit Report",  "type": "main", "index": 0},
                                                {"node": "Mark Month Audited", "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


# ─────────────────────────────────────────────────────────────────────────────
# TB-4: Risk Guardian (cada 15 min)
# Binance public ticker → calcular variação → se > 5% → alerta
# ─────────────────────────────────────────────────────────────────────────────
def workflow_tb4_risk_guardian():
    n_sched = uid()
    n_btc   = uid()
    n_code  = uid()
    n_if    = uid()
    n_gmail = uid()

    return {
        "name": "[TB] Risk Guardian — 15min",
        "nodes": [
            {
                "id": n_sched,
                "name": "Every 15 min",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 300],
                "parameters": {
                    "rule": {"interval": [{"field": "minutes", "minutesInterval": 15}]}
                },
            },
            {
                "id": n_btc,
                "name": "GET 24h Stats",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [220, 300],
                "parameters": {
                    "method": "GET",
                    "url": "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",
                    "options": {},
                },
            },
            {
                "id": n_code,
                "name": "Assess Risk",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [460, 300],
                "parameters": {
                    "jsCode": """
const data = $input.item.json;
const priceChangePercent = parseFloat(data.priceChangePercent || 0);
const lastPrice = parseFloat(data.lastPrice || 0);
const volume = parseFloat(data.volume || 0);
const quoteVolume = parseFloat(data.quoteVolume || 0);

// Níveis de risco
const absChange = Math.abs(priceChangePercent);
let riskLevel = 'baixo';
let riskEmoji = '🟢';

if (absChange > 10) { riskLevel = 'crítico'; riskEmoji = '🔴'; }
else if (absChange > 5) { riskLevel = 'alto';    riskEmoji = '🟠'; }
else if (absChange > 3) { riskLevel = 'médio';   riskEmoji = '🟡'; }

const highRisk = absChange > 5;

return {
  json: {
    priceChangePercent,
    lastPrice,
    volume,
    riskLevel,
    riskEmoji,
    highRisk,
    message: `${riskEmoji} Risco ${riskLevel.toUpperCase()}\nBTC: $${lastPrice.toFixed(0)}\nVariação 24h: ${priceChangePercent > 0 ? '+' : ''}${priceChangePercent.toFixed(2)}%\nVolume: ${(quoteVolume/1e6).toFixed(1)}M USDT`
  }
};
""",
                },
            },
            {
                "id": n_if,
                "name": "High Risk?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "position": [700, 300],
                "parameters": {
                    "conditions": {
                        "conditions": [
                            {
                                "leftValue": "={{ $json.highRisk }}",
                                "rightValue": True,
                                "operator": {"type": "boolean", "operation": "equals"},
                            }
                        ],
                        "combinator": "and",
                    }
                },
            },
            {
                "id": n_gmail,
                "name": "Risk Alert Email",
                "type": "n8n-nodes-base.gmail",
                "typeVersion": 2.1,
                "position": [940, 200],
                "parameters": {
                    "operation": "send",
                    "sendTo": "pablomaciel2003.pm@gmail.com",
                    "subject": "=🚨 Trading Risk Alert — {{ $json.riskLevel.toUpperCase() }} | BTC {{ $json.priceChangePercent.toFixed(2) }}%",
                    "emailType": "text",
                    "message": "={{ $json.message }}\n\n⚠️ Considera pausar o bot se necessário.\nAcceder ao dashboard: http://localhost:5678",
                    "options": {},
                },
                "credentials": {"gmailOAuth2": {"id": "gmail-credential", "name": "Gmail OAuth2"}},
            },
        ],
        "connections": {
            "Every 15 min": {"main": [[{"node": "GET 24h Stats", "type": "main", "index": 0}]]},
            "GET 24h Stats": {"main": [[{"node": "Assess Risk",   "type": "main", "index": 0}]]},
            "Assess Risk":   {"main": [[{"node": "High Risk?",    "type": "main", "index": 0}]]},
            "High Risk?": {"main": [[{"node": "Risk Alert Email", "type": "main", "index": 0}], []]},
        },
        "settings": {"executionOrder": "v1"},
    }


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    workflows = [
        ("WG-1: Product Discovery",  workflow_wg1_product_discovery()),
        ("WG-2: Product Upload",     workflow_wg2_product_upload()),
        ("WG-3: Price Monitor",      workflow_wg3_price_monitor()),
        ("WG-4: Weekly Report",      workflow_wg4_weekly_report()),
        ("FAT-2: Monthly Audit",     workflow_fat2_monthly_audit()),
        ("TB-4: Risk Guardian",      workflow_tb4_risk_guardian()),
    ]

    created = []
    for name, wf in workflows:
        try:
            result = create_workflow(wf)
            wf_id = result["id"]
            print(f"✅ {name} — criado (ID: {wf_id})")
            created.append({"name": name, "id": wf_id})
        except Exception as e:
            print(f"❌ {name} — erro: {e}")

    print(f"\n{'─'*50}")
    print(f"✅ {len(created)}/{len(workflows)} workflows criados")
