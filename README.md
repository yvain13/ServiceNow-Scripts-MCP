# ServiceNow Script Manager

This repository contains **two moving pieces** that work together through the [Model‑Context Protocol (MCP)](https://github.com/modelcontextprotocol):

1. **`servicenow_br_mcp_server.py`** – a FastMCP server exposing CRUD tools for ServiceNow *Business Rules* and *Client Scripts*.
2. **`script_generator.py`** – a Gradio UI that talks to the MCP server to generate, edit, and deploy scripts with GPT‑4o.

---
## Quick‑start (5 minutes)

```bash
# 1. Clone & cd
$ git clone <your‑repo> servicenow-script-manager && cd $_

# 2. Python environment (>=3.10 recommended)
$ python -m venv venv && source venv/bin/activate
$ pip install -r requirements.txt   # or pip install fastmcp gradio httpx langchain-openai python-dotenv nest_asyncio

# 3. Configure .env (create if missing)
OPENAI_API_KEY=sk-...
SERVICENOW_INSTANCE_URL=https://devXXXXXX.service-now.com/
SERVICENOW_USERNAME=admin
SERVICENOW_PASSWORD=******
SERVICENOW_AUTH_TYPE=basic
```

### 4. Run the components (two terminals)

| Terminal A | Terminal B |
|------------|-----------|
|```bash
# start FastMCP server (HTTP + SSE on :9123)
$ python servicenow_br_mcp_server.py
```|```bash
# launch Gradio UI
$ python script_generator.py
```|

Open the printed URL (default <http://127.0.0.1:7860>) and explore.

---
## How it works (architecture)

```
┌───────────────┐       SSE/HTTP        ┌────────────────────────┐
│ Gradio UI     │  ───────────────────▶ │ FastMCP Server         │
│ (script_…py)  │ ◀───────────────────  │ (servicenow_…py)       │
└───────────────┘       MCP calls       └──────────┬─────────────┘
       ▲  GPT‑4o                                    │ REST
       │                                            ▼
       └─ openai                                    ServiceNow Table API
```

1. **User** enters an instruction or selects an existing script.
2. **Gradio UI** (client) calls GPT‑4o *or* an MCP tool.
3. **FastMCP server** translates the tool call into a ServiceNow REST request.
4. Results stream back to the UI via SSE.

---
## Key scripts & commands

| File | Purpose | Run with |
|------|---------|----------|
| `servicenow_br_mcp_server.py` | Exposes `create_business_rule`, `list_business_rules`, `update_business_rule`, plus Client‑Script counterparts. | `python servicenow_br_mcp_server.py` |
| `script_generator.py` | Gradio Blocks UI: generate, AI‑edit, list, view, update. | `python script_generator.py` |
| `requirements.txt` | Python deps (FastMCP, Gradio, httpx, etc.). | `pip install -r requirements.txt` |

---
## Environment tab (optional)
The UI includes a **Environment** tab where you can change `.env` keys live. Click *Save .env* then restart both processes for changes to take effect.

---
## Connect from Claude, Windsurf, or Cursor

If you're using an MCP‑aware client (Anthropic **Claude**, **Windsurf** browser extension, **Cursor** editor, etc.) just point it to your local FastMCP server—no extra proxy needed.

Add this to your client‑side `mcp.config.json` (or equivalent):

```json
{
  "mcpServers": {
    "remote-example": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:9123/sse"
      ]
    }
  }
}
```

That's it—once the FastMCP server is running on port 9123, your editor or chat client can call `create_business_rule`, `list_client_scripts`, and the rest exactly the same way the Gradio UI does.

---
## Troubleshooting

* **401/403 from ServiceNow** – check username/password and that the user has *rest_api_explorer* or *admin* role.
* **"Event loop is closed"** – make sure you're using the provided `script_generator.py` (it runs on a shared asyncio loop).
* **Nothing happens after clicking buttons** – confirm the FastMCP server is running on `localhost:9123` (default) and reachable.

---
## License
MIT  © 2025 Your Name
