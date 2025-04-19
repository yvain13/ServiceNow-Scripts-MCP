import asyncio
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

async def main():
    # Load environment variables
    load_dotenv()

    # Create configuration dictionary
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

    # Run the query
    result = await agent.run(
        "Can you create a Client Script which alerts 'Hello World' when the form loads on  incident table?",
    )
    print(f"\nResult: {result}")

if __name__ == "__main__":
    asyncio.run(main())