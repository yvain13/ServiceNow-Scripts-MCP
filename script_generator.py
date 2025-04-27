"""ServiceNow Script Manager – Gradio + MCP
Inline *AI‑powered editing* for existing Business Rules & Client Scripts.
"""

import os, json, re, ast, functools, threading, asyncio, nest_asyncio
from dotenv import load_dotenv
import gradio as gr
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

# ───────────────────── persistent asyncio loop ─────────────────────
_main_loop = asyncio.new_event_loop()
nest_asyncio.apply()
threading.Thread(target=lambda l: (asyncio.set_event_loop(l), l.run_forever()), args=(_main_loop,), daemon=True).start()

def sync(coro):
    return asyncio.run_coroutine_threadsafe(coro, _main_loop).result()

# ───────────────────── MCP + LLM helpers ───────────────────────────
load_dotenv()

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
            f"Here is an existing ServiceNow {'client script' if stype=='Client Script' else 'business rule'}:\n\n"
            f"```javascript\n{base_script}\n```\n\nInstruction: {instr}.\n"
            "Return only the edited script (no markdown)."
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
        f"List the top 5 {'client scripts' if stype=='Client Script' else 'business rules'} in ServiceNow that match '{query}'"+
        (f" for the {table} table" if table else "")+
        "\n\nReturn ONLY JSON list [{ 'name':'', 'sys_id':'', 'table':'' }]."
    )
    raw = await agent.run(nat_q)
    data=[]
    if isinstance(raw,list):
        data=raw
    elif isinstance(raw,str):
        try:
            data=json.loads(raw)
        except json.JSONDecodeError:
            m=re.search(r"\[\s*\{.*?}\s*]",raw,re.DOTALL)
            if m:
                data=ast.literal_eval(m.group(0))
    choices=[(d.get("name","Unnamed"),d.get("sys_id","")) for d in data if d.get("sys_id")]
    return gr.update(choices=choices,value=None)

async def get_script(stype, sys_id):
    agent,_=create_mcp_client()
    q=(f"Get the {'client script' if stype=='Client Script' else 'business rule'} with sys_id {sys_id} "
       "from ServiceNow and return JSON with keys name, sys_id, table, script, active, description.")
    raw=await agent.run(q)
    try:
        return json.loads(raw) if isinstance(raw,str) else raw
    except json.JSONDecodeError:
        m=re.search(r"\{.*}\s*",raw,re.DOTALL)
        return json.loads(m.group(0)) if m else {}

async def update_script(sys_id, script, stype):
    agent,_=create_mcp_client()
    q=f"""Update the {'client script' if stype=='Client Script' else 'business rule'} with sys_id {sys_id} in ServiceNow\n\n{script}\n\nReturn JSON {{success, sys_id, message}}."""
    raw=await agent.run(q)
    try:
        return json.loads(raw) if isinstance(raw,str) else raw
    except Exception:
        return {"success":False,"message":raw[:120]}

# ───────────────────── sync wrappers ──────────────────────────────

def process_generate(i,s,t): return sync(generate_script(i,s,t))
def process_create(s,st,t,i): return sync(create_on_platform(s,st,t,i))
def process_list(st,t,q): return sync(list_scripts(st,t,q))

def script_selected(sys_id,stype):
    if not sys_id: return "","","",""
    res=sync(get_script(stype,sys_id))
    return res.get("script",""),sys_id,res.get("name",""),res.get("table","")

def process_update(sid,script,stype):
    out=sync(update_script(sid,script,stype)) if sid else {"success":False,"message":"No sys_id"}
    return ("✅ " if out.get("success") else "❌ ")+out.get("message","Unknown")

def process_ai_edit(instr,current_script,stype,table):
    if not current_script.strip():
        return "No script loaded to edit!"
    return sync(generate_script(instr,stype,table,base_script=current_script))

# ────────────────────── UI ───────────────────────────────────────
with gr.Blocks(title="ServiceNow Script Manager") as app:
    sel_id   = gr.Textbox(visible=False)
    sel_name = gr.Textbox(visible=False)
    sel_tbl  = gr.Textbox(visible=False)

    gr.Markdown("# ServiceNow Script Manager")

    with gr.Tabs():
        # Create tab
        with gr.TabItem("Create Script"):
            with gr.Row():
                with gr.Column():
                    instr=gr.Textbox(label="Instruction",lines=3)
                    stype_create=gr.Dropdown(["Client Script","Business Rule"],value="Client Script",label="Type")
                    table_create=gr.Textbox(label="Table",value="incident")
                    gen_btn=gr.Button("Generate",variant="primary")
                with gr.Column():
                    script_box=gr.Textbox(label="Generated Script",lines=15)
                    create_btn=gr.Button("Create on Platform")
                    create_res=gr.Textbox(label="Result",lines=3)
        # Business Rules tab
        with gr.TabItem("Manage Business Rules"):
            with gr.Row():
                with gr.Column(scale=1):
                    q_br=gr.Textbox(label="Search",value="AI")
                    tbl_br=gr.Textbox(label="Table (opt)")
                    list_br=gr.Button("Search BRs")
                    br_radio=gr.Radio(label="Business Rules",interactive=True)
                with gr.Column(scale=2):
                    br_info=gr.Markdown()
                    br_script=gr.Textbox(label="Script",lines=20)
                    br_edit_instr=gr.Textbox(label="AI Edit Instruction",placeholder="e.g., add null check…")
                    br_ai_btn=gr.Button("AI Update Script")
                    upd_br=gr.Button("Save to ServiceNow",variant="primary")
                    upd_br_res=gr.Textbox(label="Update result")
        # Client Scripts tab
        with gr.TabItem("Manage Client Scripts"):
            with gr.Row():
                with gr.Column(scale=1):
                    q_cs=gr.Textbox(label="Search",value="AI")
                    tbl_cs=gr.Textbox(label="Table (opt)")
                    list_cs=gr.Button("Search CSs")
                    cs_radio=gr.Radio(label="Client Scripts",interactive=True)
                with gr.Column(scale=2):
                    cs_info=gr.Markdown()
                    cs_script=gr.Textbox(label="Script",lines=20)
                    cs_edit_instr=gr.Textbox(label="AI Edit Instruction",placeholder="Describe change…")
                    cs_ai_btn=gr.Button("AI Update Script")
                    upd_cs=gr.Button("Save to ServiceNow",variant="primary")
                    upd_cs_res=gr.Textbox(label="Update result")

    # Wiring create tab
    gen_btn.click(process_generate,[instr,stype_create,table_create],script_box)
    create_btn.click(process_create,[script_box,stype_create,table_create,instr],create_res)
    # Wiring Business Rules
    list_br.click(functools.partial(process_list,"Business Rule"),[tbl_br,q_br],br_radio)
    br_radio.change(functools.partial(script_selected,stype="Business Rule"),br_radio,[br_script,sel_id,sel_name,sel_tbl]).then(lambda n,t:f"**Selected:** {n} ({t})" if t else f"**Selected:** {n}",[sel_name,sel_tbl],br_info)
    br_ai_btn.click(process_ai_edit,[br_edit_instr,br_script,gr.State("Business Rule"),tbl_br],br_script)
    upd_br.click(functools.partial(process_update,stype="Business Rule"),[sel_id,br_script],upd_br_res)
    # Wiring Client Scripts
    list_cs.click(functools.partial(process_list, "Client Script"), [tbl_cs, q_cs], cs_radio)
    cs_radio.change(functools.partial(script_selected, stype="Client Script"), cs_radio, [cs_script, sel_id, sel_name, sel_tbl]).then(
        lambda n, t: f"**Selected:** {n} ({t})" if t else f"**Selected:** {n}",
        [sel_name, sel_tbl],
        cs_info,
    )
    cs_ai_btn.click(process_ai_edit, [cs_edit_instr, cs_script, gr.State("Client Script"), tbl_cs], cs_script)
    upd_cs.click(functools.partial(process_update, stype="Client Script"), [sel_id, cs_script], upd_cs_res)

if __name__ == "__main__":
    app.launch()
