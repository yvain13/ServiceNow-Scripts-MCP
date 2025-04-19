import asyncio
import gradio as gr
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create configuration dictionary for ServiceNow MCP
def create_mcp_client():
    config = {
        "mcpServers": {
            "servicenow-mcp": {
                "command": "/opt/anaconda3/bin/python",
                "args": [
                    "-m",
                    "servicenow_mcp.cli"
                ],
                "env": {
                    "SERVICENOW_INSTANCE_URL": os.getenv("SERVICENOW_INSTANCE_URL"),
                    "SERVICENOW_USERNAME": os.getenv("SERVICENOW_USERNAME"),
                    "SERVICENOW_PASSWORD": os.getenv("SERVICENOW_PASSWORD"),
                    "SERVICENOW_AUTH_TYPE": os.getenv("SERVICENOW_AUTH_TYPE")
                }
            }
        }
    }
    
    # Create MCPClient from configuration dictionary
    client = MCPClient.from_dict(config)
    
    # Create LLM
    llm = ChatOpenAI(model="gpt-4o")
    
    # Create agent with the client
    agent = MCPAgent(llm=llm, client=client, max_steps=30)
    
    return agent, llm


async def generate_script(instruction, script_type, table_name):
    """
    First generate a script using GPT-4o directly,
    then use that script to create it on ServiceNow via MCP
    """
    agent, llm = create_mcp_client()
    
    # Step 1: Generate the script using GPT-4o directly
    if script_type == "Client Script":
        prompt = f"""
        Write a ServiceNow Client Script that {instruction} on the {table_name} table.
        Only include the script content, no explanation. 
        Format it properly with appropriate JavaScript syntax.
        """
    else:  # Business Rule
        prompt = f"""
        Write a ServiceNow Business Rule script that {instruction} for the {table_name} table.
        Only include the script content, no explanation.
        Format it properly with appropriate JavaScript syntax.
        """
    
    # Get the script from GPT-4o
    script_response = await llm.ainvoke(prompt)
    generated_script = script_response.content
    
    return generated_script


async def create_on_platform(script_text, script_type, table_name, instruction):
    """Create the script on the ServiceNow platform using MCP"""
    agent, _ = create_mcp_client()
    
    # Create query to implement the script
    if script_type == "Client Script":
        query = f"Create this client script on the {table_name} table in ServiceNow with the following script content: {script_text}. The client script should {instruction}."
    else:  # Business Rule
        query = f"Create this business rule on the {table_name} table in ServiceNow with the following script content: {script_text}. The business rule should {instruction}."
    
    # Run the query
    result = await agent.run(query)
    
    return result


def process_generate(instruction, script_type, table_name):
    """Process the generate button click"""
    return asyncio.run(generate_script(instruction, script_type, table_name))


def process_create(script_text, script_type, table_name, instruction):
    """Process the create on platform button click"""
    return asyncio.run(create_on_platform(script_text, script_type, table_name, instruction))


# Create Gradio interface
with gr.Blocks(title="ServiceNow Script Generator") as app:
    gr.Markdown("# ServiceNow Script Generator")
    gr.Markdown("Generate and deploy Client Scripts and Business Rules for ServiceNow")
    
    with gr.Row():
        with gr.Column():
            instruction = gr.Textbox(label="Instruction", 
                                    placeholder="Describe what you want the script to do...",
                                    lines=3)
            
            script_type = gr.Dropdown(
                choices=["Client Script", "Business Rule"],
                label="Script Type",
                value="Client Script"
            )
            
            table_name = gr.Textbox(
                label="Table Name",
                placeholder="e.g., incident, problem, change_request",
                value="incident"
            )
            
            generate_btn = gr.Button("Generate Script", variant="primary")
        
        with gr.Column():
            script_output = gr.Textbox(
                label="Generated Script", 
                lines=15,
                interactive=True,
                placeholder="Generated script will appear here..."
            )
            
            create_btn = gr.Button("Create on Platform", variant="secondary")
            
            result_output = gr.Textbox(
                label="Result",
                lines=5,
                interactive=False
            )
    
    # Set up event handlers
    generate_btn.click(
        fn=process_generate, 
        inputs=[instruction, script_type, table_name],
        outputs=script_output
    )
    
    create_btn.click(
        fn=process_create,
        inputs=[script_output, script_type, table_name, instruction],
        outputs=result_output
    )

# Launch the app
if __name__ == "__main__":
    app.launch()
