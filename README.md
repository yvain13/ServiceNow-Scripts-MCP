# ServiceNow Script Manager

This repository contains **two moving pieces** that work together through the [Model‑Context Protocol (MCP)](https://github.com/modelcontextprotocol):

1. **`sn_mcp_tools.py`** – a FastMCP server exposing CRUD tools for ServiceNow *Business Rules* and *Client Scripts*.
2. **`script_generator.py`** – a Gradio UI that talks to the MCP server to generate, edit, and deploy scripts with GPT‑4o.

---
## Quick‑start (5 minutes)

```bash
# 1. Clone & cd
$ git clone <your‑repo> servicenow-script-manager && cd $_

# 2. Python environment (>=3.10 recommended)
$ python -m venv venv && source venv/bin/activate
$ pip install -r requirements.txt   # includes fastmcp, gradio, httpx, langchain-openai, python-dotenv, nest_asyncio, mcp-use

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
$ python sn_mcp_tools.py
```|```bash
# launch Gradio UI
$ python script_generator.py
```|

Open the printed URL (default <http://127.0.0.1:7860>) and explore.

---
## Detailed Setup Guide

Follow these steps to get the solution up and running from scratch:

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/servicenow-script-manager.git
cd servicenow-script-manager
```

### 2. Set Up Python Environment

Make sure you have Python 3.10 or newer installed. Then create and activate a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate on macOS/Linux
source venv/bin/activate

# Activate on Windows
# venv\Scripts\activate
```

### 3. Install Dependencies

Install all required packages:

```bash
pip install -r requirements.txt
```

This will install fastmcp, gradio, httpx, langchain-openai, python-dotenv, nest_asyncio, and mcp-use.

### 4. Set Up Environment Variables

Create a file named `.env` in the root directory with the following content:

```
# OpenAI API Key for GPT-4o
OPENAI_API_KEY=sk-your-api-key-here

# ServiceNow Instance Details
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com/
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
SERVICENOW_AUTH_TYPE=basic  # or oauth depending on your setup
```

Replace the placeholder values with your actual credentials.

### 5. Start the FastMCP Server

Open a terminal window and run:

```bash
python sn_mcp_tools.py
```

You should see output indicating that the server is running and listening on port 9123.

### 6. Start the Gradio UI

In a second terminal window (with the virtual environment activated), run:

```bash
python script_generator.py
```

The output will include a URL (typically http://127.0.0.1:7860) that you can open in your browser.

### 7. Access the UI

Open the URL in your browser and you should see the ServiceNow Script Manager interface with tabs for:
- Creating new scripts
- Managing business rules
- Managing client scripts

### 8. Example Usage

1. **Creating a new script**: 
   - Go to the "Create Script" tab
   - Enter an instruction like "Log when a high priority incident is created"
   - Select the script type and table
   - Click "Generate" and then "Create on Platform" once satisfied

2. **Viewing existing scripts**:
   - Go to the "Manage Business Rules" or "Manage Client Scripts" tab
   - Enter a search term and click the search button
   - Select a script from the list to view and edit

3. **Updating a script**:
   - After selecting a script, modify it directly or use the AI editing feature
   - Click "Save to ServiceNow" to update the script on your instance

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
## Key scripts & commands

| File | Purpose | Run with |
|------|---------|----------|
| `sn_mcp_tools.py` | Exposes `create_business_rule`, `list_business_rules`, `update_business_rule`, plus Client‑Script counterparts. | `python sn_mcp_tools.py` |
| `script_generator.py` | Gradio Blocks UI: generate, AI‑edit, list, view, update. | `python script_generator.py` |
| `mcp_client.py` | Example script showing how to create an MCPAgent instance that connects to the FastMCP server. | `python mcp_client.py` |
| `requirements.txt` | Python deps (FastMCP, Gradio, httpx, etc.). | `pip install -r requirements.txt` |

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
MIT  2025 Tushar Mishra
