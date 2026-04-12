"""n8n Workflow Entegrasyonu — Jarvis API Webhook Şemaları.

Bu dosya n8n'e import edilebilecek workflow JSON şemalarını tanımlar.
n8n Dashboard → Workflows → Import from JSON ile içe aktarılabilir.
"""

N8N_WORKFLOW_CLONE = {
    "name": "Jarvis — Site Klonlama",
    "nodes": [
        {
            "type": "n8n-nodes-base.webhook",
            "name": "Klonlama Tetikleyici",
            "parameters": {"path": "clone-trigger", "method": "POST"},
            "position": [240, 300],
        },
        {
            "type": "n8n-nodes-base.httpRequest",
            "name": "Jarvis Clone API",
            "parameters": {
                "method": "POST",
                "url": "http://localhost:8000/api/v2/workspace/clone",
                "body": {
                    "url": "={{$json.url}}",
                    "extract_components": True,
                },
                "options": {"timeout": 120},
            },
            "position": [460, 300],
        },
        {
            "type": "n8n-nodes-base.if",
            "name": "Başarılı mı?",
            "parameters": {
                "conditions": {
                    "boolean": [{"value1": "={{$json.success}}"}]
                }
            },
            "position": [680, 300],
        },
    ],
    "connections": {
        "Klonlama Tetikleyici": {
            "main": [[{"node": "Jarvis Clone API", "type": "main", "index": 0}]]
        },
        "Jarvis Clone API": {
            "main": [[{"node": "Başarılı mı?", "type": "main", "index": 0}]]
        },
    },
}

N8N_WORKFLOW_GENERATE = {
    "name": "Jarvis — Fikir → Uygulama",
    "nodes": [
        {
            "type": "n8n-nodes-base.webhook",
            "name": "Fikir Webhook",
            "parameters": {"path": "generate-app", "method": "POST"},
            "position": [240, 300],
        },
        {
            "type": "n8n-nodes-base.httpRequest",
            "name": "Jarvis Generate API",
            "parameters": {
                "method": "POST",
                "url": "http://localhost:8000/api/v2/workspace/generate",
                "body": {
                    "idea": "={{$json.idea}}",
                    "tech_stack": "={{$json.tech_stack || 'html-css-js'}}",
                },
                "options": {"timeout": 180},
            },
            "position": [460, 300],
        },
    ],
    "connections": {
        "Fikir Webhook": {
            "main": [[{"node": "Jarvis Generate API", "type": "main", "index": 0}]]
        },
    },
}

N8N_WORKFLOW_SYNTHESIZE = {
    "name": "Jarvis — Hibrit RAG Sentezi",
    "nodes": [
        {
            "type": "n8n-nodes-base.webhook",
            "name": "Sentez Komutu",
            "parameters": {"path": "synthesize", "method": "POST"},
            "position": [240, 300],
        },
        {
            "type": "n8n-nodes-base.httpRequest",
            "name": "Jarvis Synthesize API",
            "parameters": {
                "method": "POST",
                "url": "http://localhost:8000/api/v2/workspace/synthesize",
                "body": {
                    "user_command": "={{$json.command}}",
                    "target_project": "={{$json.project_name}}",
                },
                "options": {"timeout": 180},
            },
            "position": [460, 300],
        },
    ],
    "connections": {
        "Sentez Komutu": {
            "main": [[{"node": "Jarvis Synthesize API", "type": "main", "index": 0}]]
        },
    },
}

# Tüm workflow'lar — dışa aktarma için
ALL_WORKFLOWS = [
    N8N_WORKFLOW_CLONE,
    N8N_WORKFLOW_GENERATE,
    N8N_WORKFLOW_SYNTHESIZE,
]
