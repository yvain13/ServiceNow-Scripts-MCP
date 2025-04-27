"""ServiceNow Script Manager – Gradio + MCP
Full version with an **Environment** tab to view/update .env variables.
"""

import os, json, re, ast, threading, asyncio, functools, nest_asyncio
from pathlib import Path
from dotenv import load_dotenv, set_key
import gradio as gr
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

# ──────────────────────── Shared event loop ───────────────────────
_main_loop = asyncio.new_event_loop()
nest_asyncio.apply()
threading.Thread(target=lambda l: (asyncio.set_event_loop(l), l.run_forever()), args=(_main_loop,), daemon=True).start()

def sync(coro):
    return asyncio.run_coroutine_threadsafe(coro, _main_loop).result()

# ──────────────────────── .env helpers ────────────────────────────
DOTENV_FILE = Path(".env")
load_dotenv()

def save_env(vars_dict: dict):
    if not DOTENV_FILE.exists():
        DOTENV_FILE.touch()
    for k, v in vars_dict.items():
        set_key(str(DOTENV_FILE), k, v)
        os.environ[k] = v
    load_dotenv(override=True)

# ──────────────────────── MCP / LLM helpers ───────────────────────

def create_mcp_client():
    cfg = {"mcpServers": {"http": {"url": "http://localhost:9123/sse"}}}
    client = MCPClient.from_dict(cfg)
    llm = ChatOpenAI(model="gpt-4o")
    return MCPAgent(llm=llm, client=client, max_steps=30), llm

async def generate_script(instr, stype, table, base_script=None):
    agent, llm = create_mcp_client()
    if base_script is None:
        prompt = (
            f"Write a ServiceNow {'Client Script' if stype=='Client Script' else 'Business Rule'} "
            f"that {instr} on/for the {table} table. Only script, no explanation."
        )
    else:
        prompt = (
            f"Here is an existing {'client script' if stype=='Client Script' else 'business rule'}:\n\n"
            f"```javascript\n{base_script}\n```\n\nInstruction: {instr}.\n"
            "Return only the edited script."
        )
    return (await llm.ainvoke(prompt)).content

async def create_on_platform(script, stype, table, instr):
    agent, _ = create_mcp_client()
    name = f"AI {instr[:30]}"
    q = (
        f"Create this {'client script' if stype=='Client Script' else 'business rule'} "
        f"on the {table} table with name '{name}' and the following script: {script}"
    )
    return await agent.run(q)

async def list_scripts(stype, table, query):
    agent, _ = create_mcp_client()
    nat_q = (
        f"List top 5 {'client scripts' if stype=='Client Script' else 'business rules'} matching '{query}'" +
        (f" for {table} table" if table else "") +
        "\nReturn JSON list [{ 'name':'', 'sys_id':'', 'table':'' }]."
    )
    raw = await agent.run(nat_q)
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        m = re.search(r"\[.*]", raw, re.DOTALL)
        data = ast.literal_eval(m.group(0)) if m else []
    choices = [(d['name'], d['sys_id']) for d in data if d.get('sys_id')]
    return gr.update(choices=choices, value=None)

async def get_script(stype, sys_id):
    agent, _ = create_mcp_client()
    q = f"Get {stype.lower()} with sys_id {sys_id} as JSON (name, sys_id, table, script)"
    raw = await agent.run(q)
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except:
        return {}

async def update_script(sys_id, script, stype):
    agent, _ = create_mcp_client()
    q = f"Update {stype.lower()} {sys_id} with script: {script}\nReturn JSON {{success, message}}"
    raw = await agent.run(q)
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except:
        return {"success": False, "message": raw[:120]}

# wrappers
process_generate = lambda i,s,t: sync(generate_script(i,s,t))
process_create   = lambda s,st,t,i: sync(create_on_platform(s,st,t,i))
process_list     = lambda st,t,q: sync(list_scripts(st,t,q))
process_ai_edit  = lambda instr,code,st,tbl: "No script loaded" if not code.strip() else sync(generate_script(instr,st,tbl,code))

def script_selected(sys_id, st):
    if not sys_id: return "","","",""
    res = sync(get_script(st, sys_id))
    return res.get('script',''), sys_id, res.get('name',''), res.get('table','')

def process_update(sid, code, st):
    res = sync(update_script(sid, code, st)) if sid else {"success":False,"message":"No sys_id"}
    return ("✅ " if res.get('success') else "❌ ")+res.get('message','')

def process_save_env(openai,url,user,pwd,auth):
    save_env({
        "OPENAI_API_KEY":openai,
        "SERVICENOW_INSTANCE_URL":url,
        "SERVICENOW_USERNAME":user,
        "SERVICENOW_PASSWORD":pwd,
        "SERVICENOW_AUTH_TYPE":auth,
    })
    return "✅ Saved (restart may be required)"

# ───────────────────────────── UI ────────────────────────────────
with gr.Blocks(title="ServiceNow Script Manager") as app:
    sel_id = gr.Textbox(visible=False)
    sel_name = gr.Textbox(visible=False)
    sel_table = gr.Textbox(visible=False)

    gr.Markdown("# ServiceNow Script Manager")

    with gr.Tabs():
        # Tab 1 Create
        with gr.TabItem("Create Script"):
            with gr.Row():
                with gr.Column():
                    instr = gr.Textbox(label="Instruction", lines=3)
                    stype_c = gr.Dropdown(["Client Script","Business Rule"], value="Client Script")
                    tbl_c   = gr.Textbox(value="incident", label="Table")
                    gen_btn = gr.Button("Generate", variant="primary")
                with gr.Column():
                    gen_code = gr.Textbox(label="Generated Script", lines=15)
                    create_btn = gr.Button("Create on Platform")
                    create_res = gr.Textbox(label="Result")
        # Tab 2 BR
        with gr.TabItem("Manage Business Rules"):
            with gr.Row():
                with gr.Column(scale=1):
                    q_br   = gr.Textbox(label="Search")
                    tbl_br = gr.Textbox(label="Table (opt)")
                    list_br= gr.Button("Search")
                    br_radio = gr.Radio(label="Business Rules", interactive=True)
                with gr.Column(scale=2):
                    br_info = gr.Markdown()
                    br_code = gr.Textbox(label="Code", lines=18)
                    br_instr= gr.Textbox(label="AI Edit Instruction")
                    br_ai   = gr.Button("AI Update Script")
                    br_save = gr.Button("Save to SN", variant="primary")
                    br_res  = gr.Textbox(label="Result")
        # Tab 3 CS
        with gr.TabItem("Manage Client Scripts"):
            with gr.Row():
                with gr.Column(scale=1):
                    q_cs   = gr.Textbox(label="Search")
                    tbl_cs = gr.Textbox(label="Table (opt)")
                    list_cs= gr.Button("Search")
                    cs_radio = gr.Radio(label="Client Scripts", interactive=True)
                with gr.Column(scale=2):
                    cs_info = gr.Markdown()
                    cs_code = gr.Textbox(label="Code", lines=18)
                    cs_instr= gr.Textbox(label="AI Edit Instruction")
                    cs_ai   = gr.Button("AI Update Script")
                    cs_save = gr.Button("Save to SN", variant="primary")
                    cs_res  = gr.Textbox(label="Result")
        # Tab 4 Environment
        with gr.TabItem("Environment"):
            env_openai = gr.Textbox(label="OPENAI_API_KEY", type="password",value=os.getenv("OPENAI_API_KEY",""))
            env_url    = gr.Textbox(label="SERVICENOW_INSTANCE_URL", value=os.getenv("SERVICENOW_INSTANCE_URL",""))
            env_user   = gr.Textbox(label="SERVICENOW_USERNAME", value=os.getenv("SERVICENOW_USERNAME",""))
            env_pwd    = gr.Textbox(label="SERVICENOW_PASSWORD", type="password", value=os.getenv("SERVICENOW_PASSWORD",""))
            env_auth   = gr.Dropdown(["basic","oauth"], value=os.getenv("SERVICENOW_AUTH_TYPE","basic"), label="SERVICENOW_AUTH_TYPE")
            save_env_btn = gr.Button("Save .env", variant="primary")
            env_status   = gr.Markdown()

    # Wiring Create
    gen_btn.click(process_generate, [instr, stype_c, tbl_c], gen_code)
    create_btn.click(process_create, [gen_code, stype_c, tbl_c, instr], create_res)
    # Wiring BR
    list_br.click(functools.partial(process_list,"Business Rule"), [tbl_br, q_br], br_radio)
    br_radio.change(functools.partial(script_selected, st="Business Rule"), br_radio, [br_code, sel_id, sel_name, sel_table]).then(
        lambda n,t: f"**Selected:** {n} ({t})" if t else f"**Selected:** {n}", [sel_name, sel_table], br_info)
    br_ai.click(process_ai_edit, [br_instr, br_code, gr.State("Business Rule"), tbl_br], br_code)
    br_save.click(functools.partial(process_update, st="Business Rule"), [sel_id, br_code], br_res)
    # Wiring CS
    list_cs.click(functools.partial(process_list,"Client Script"), [tbl_cs, q_cs], cs_radio)
    cs_radio.change(functools.partial(script_selected, st="Client Script"), cs_radio, [cs_code, sel_id, sel_name, sel_table]).then(
        lambda n,t: f"**Selected:** {n} ({t})" if t else f"**Selected:** {n}", [sel_name, sel_table], cs_info)
    cs_ai.click(process_ai_edit, [cs_instr, cs_code, gr.State("Client Script"), tbl_cs], cs_code)
    cs_save.click(functools.partial(process_update, st="Client Script"), [sel_id, cs_code], cs_res)
    # Wiring Env
    save_env_btn.click(process_save_env, [env_openai, env_url, env_user, env_pwd, env_auth], env_status)

if __name__ == "__main__":
    app.launch()
