"""Read-only MCP server for fictional job records."""
import json
from pathlib import Path
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

server = MCPServer("Fictional Crew Job Records")
INDEX = json.loads(Path(__file__).with_name("records.json").read_text())

@server.tool()
def get_job_records(job_id: str) -> str:
    """Return only the records for this fictional job, in chronological order."""
    return json.dumps(INDEX.get(job_id, []), separators=(",", ":"))

if __name__ == "__main__":
    server.run(transport="stdio")
