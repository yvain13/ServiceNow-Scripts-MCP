# ServiceNow Script Manager

This repository contains **two moving pieces** that work together through the [Model‑Context Protocol (MCP)](https://github.com/modelcontextprotocol):

1. **`sn_mcp_tools.py`** – a FastMCP server exposing CRUD tools for ServiceNow *Business Rules*, *Client Scripts*, and *Script Includes*.
2. **`script_generator.py`** – a Gradio UI that talks to the MCP server to generate, edit, and deploy scripts with GPT‑4o.

---
## Setup Guide

Follow these simple steps to get the solution up and running:

### 1. Clone the Repository

```bash
git clone https://github.com/yvain13/ServiceNow-Scripts-MCP.git
cd ServiceNow-Scripts-MCP
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate on macOS/Linux
source venv/bin/activate

# Activate on Windows
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a file named `.env` in the root directory with your credentials:

```
# OpenAI API Key
OPENAI_API_KEY=sk-your-api-key-here

# ServiceNow Instance Details
SERVICENOW_URL=https://your-instance.service-now.com/
SERVICENOW_USER=your-username
SERVICENOW_PASS=your-password
SERVICENOW_AUTH_TYPE=basic
```

### 4. Start the Application

Run these commands in separate terminal windows:

```bash
# Terminal 1: Start the FastMCP server
python sn_mcp_tools.py

# Terminal 2: Start the Gradio UI
python script_generator.py
```

Open the URL shown in the second terminal (typically http://127.0.0.1:7860) in your web browser.

---
## How it works (architecture)

```
┌───────────────┐       HTTP/MCP        ┌────────────────────────┐
│ Gradio UI     │  ───────────────────▶ │ FastMCP Server         │
│ (script_…py)  │ ◀───────────────────  │ (sn_mcp_tools.py)      │
└───────────────┘       MCP calls       └──────────┬─────────────┘
       ▲  GPT‑4o                                    │ REST API
       │                                            ▼
       └─ openai                                    ServiceNow Table API
```

1. **User** enters an instruction or selects an existing script.
2. **Gradio UI** (client) calls GPT‑4o *or* an MCP tool.
3. **FastMCP server** translates the tool call into a ServiceNow REST request.
4. Results stream back to the UI via HTTP.

---
## Key Files

| File | Purpose | Run with |
|------|---------|----------|
| `sn_mcp_tools.py` | Exposes ServiceNow CRUD operations for scripts via MCP | `python sn_mcp_tools.py` |
| `script_generator.py` | Gradio UI for script management | `python script_generator.py` |
| `mcp_client.py` | Example showing how to create an MCPAgent | `python mcp_client.py` |
| `requirements.txt` | Python dependencies | `pip install -r requirements.txt` |

---
## Example MCP Client Usage

The `mcp_client.py` file provides a simple example of how to create an MCPAgent that can communicate with your FastMCP server. This is especially useful for developers who want to build their own applications that leverage the ServiceNow tools without using the Gradio UI.

```python
# Example usage from mcp_client.py
from mcp_use import MCPAgent, MCPClient
from langchain_openai import ChatOpenAI

# Create a client that connects to the FastMCP server
config = {
    "mcpServers": {
        "http": {
            "url": "http://localhost:9123/mcp"
        }
    }
}
client = MCPClient.from_dict(config)

# Create the LLM
llm = ChatOpenAI(model="gpt-4o")

# Create the agent
agent = MCPAgent(llm=llm, client=client, max_steps=30)

# Run a query that will use the MCP tools
result = agent.run("Create a business rule for the incident table that logs when a VIP incident is created")
print(result)
```

You can use this pattern to integrate ServiceNow tool access in any Python application or script.

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
        "http://localhost:9123/mcp"
      ]
    }
  }
}
```

That's it—once the FastMCP server is running on port 9123, your editor or chat client can call the available tools exactly the same way the Gradio UI does.

## Available MCP Tools

The FastMCP server provides comprehensive CRUD operations for ServiceNow scripts:

### Business Rules
- `create_business_rule(name, table, script, when, active, description)` - Create a new business rule
- `list_business_rules(query, table, limit)` - List business rules with filtering
- `update_business_rule(sys_id, script, name, table, when, active, description)` - Update existing business rule
- `get_business_rule(sys_id)` - Get specific business rule by sys_id

### Client Scripts
- `create_client_script(name, table, script, type, active, description)` - Create a new client script
- `list_client_scripts(query, table, limit)` - List client scripts with filtering
- `update_client_script(sys_id, script, name, table, type, active, description)` - Update existing client script
- `get_client_script(sys_id)` - Get specific client script by sys_id

### Script Includes
- `create_script_include(name, script, active, description)` - Create a new script include
- `update_script_include(sys_id, script, name, active, description)` - Update existing script include
- `get_script_include(sys_id)` - Get specific script include by sys_id

All tools include proper error handling, authentication, and detailed logging for debugging.

---
## Troubleshooting

* **401/403 from ServiceNow** – check username/password and that the user has *rest_api_explorer* or *admin* role.
* **"Event loop is closed"** – make sure you're using the provided `script_generator.py` (it runs on a shared asyncio loop).
* **Nothing happens after clicking buttons** – confirm the FastMCP server is running on `localhost:9123` (default) and reachable.

---
## License
MIT  2025 Tushar Mishra
