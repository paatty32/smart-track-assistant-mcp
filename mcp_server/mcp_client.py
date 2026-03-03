from llama_index.tools.mcp import BasicMCPClient, McpToolSpec

async def get_weather_tools():
    mcp_weather_client = BasicMCPClient("http://0.0.0.0:8000/mcp")
    mcp_weather_tools = McpToolSpec(client=mcp_weather_client)

    tools = await mcp_weather_tools.to_tool_list_async()
    return tools