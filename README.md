# ServiceNow Script Manager

This repository contains **two moving pieces** that work together through the [Model‑Context Protocol (MCP)](https://github.com/modelcontextprotocol):

1. **`sn_mcp_tools.py`** – a FastMCP server exposing CRUD tools for ServiceNow *Business Rules* and *Client Scripts*.
2. **`script_generator.py`** – a Gradio UI that talks to the MCP server to generate, edit, and deploy scripts with GPT‑4o.

---
## Setup Guide

Follow these simple steps to get the solution up and running:

### 1. Clone the Repository

```bash
git clone https://github.com/yvain13/MCP-Use-with-SN.git
cd MCP-Use-with-SN
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
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com/
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
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
┌───────────────┐       SSE/HTTP        ┌────────────────────────┐
│ Gradio UI     │  ───────────────────▶ │ FastMCP Server         │
│ (script_…py)  │ ◀───────────────────  │ (sn_mcp_tools.py)      │
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
            "url": "http://localhost:9123/sse"
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
MIT  2025 Tushar Mishra
