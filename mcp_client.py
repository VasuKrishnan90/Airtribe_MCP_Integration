"""
Standard MCP Client & Multi-Server Manager
==========================================
Provides standardized client interfaces for connecting to, discovering, and
invoking tools and resources across multiple JSON-RPC 2.0 MCP servers via Stdio.
"""

import sys
import json
import asyncio
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.types import TextContent


class MCPClient:
    """A single MCP Server connection client managing session lifecycle over Stdio."""

    def __init__(self, name: str, script_path: str, python_path: Optional[str] = None):
        self.name = name
        self.script_path = script_path
        self.python_path = python_path or sys.executable
        self._session: Optional[ClientSession] = None
        self._stdio_context = None
        self._session_context = None
        self.tools: Dict[str, Any] = {}
        self.resources: List[Any] = []

    async def connect(self):
        """Establish stdio connection and initialize the MCP session."""
        server_params = StdioServerParameters(
            command=self.python_path,
            args=[self.script_path]
        )
        self._stdio_context = stdio_client(server_params)
        read_stream, write_stream = await self._stdio_context.__aenter__()

        self._session_context = ClientSession(read_stream, write_stream)
        self._session = await self._session_context.__aenter__()

        # Handshake & Discovery
        await self._session.initialize()
        tools_result = await self._session.list_tools()
        self.tools = {t.name: t for t in tools_result.tools}

        try:
            resources_result = await self._session.list_resources()
            self.resources = resources_result.resources
        except Exception:
            self.resources = []

        return self

    async def disconnect(self):
        """Safely close session and stdio streams."""
        if self._session_context:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception:
                pass
        if self._stdio_context:
            try:
                await self._stdio_context.__aexit__(None, None, None)
            except Exception:
                pass
        self._session = None

    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """
        Call a tool on the MCP server and parse its response.
        Automatically converts JSON-encoded TextContent to native Python objects.
        """
        if not self._session:
            raise ConnectionError(f"MCPClient '{self.name}' is not connected.")

        result = await self._session.call_tool(tool_name, arguments=arguments or {})

        # Handle MCP Tool Error flag (supports both snake_case and camelCase)
        if getattr(result, "is_error", False) or getattr(result, "isError", False):
            err_msg = "Tool execution error"
            if hasattr(result, "content") and result.content:
                err_msg = getattr(result.content[0], "text", str(result.content[0]))
            raise RuntimeError(f"MCP Tool Error [{tool_name}]: {err_msg}")
        
        # If there are content items returned
        if hasattr(result, "content") and result.content:
            parsed_items = []
            for item in result.content:
                if isinstance(item, TextContent):
                    text = item.text
                    # Attempt JSON parse
                    try:
                        parsed_items.append(json.loads(text))
                    except (json.JSONDecodeError, TypeError):
                        parsed_items.append(text)
                else:
                    parsed_items.append(getattr(item, "text", str(item)))

            return parsed_items[0] if len(parsed_items) == 1 else parsed_items

        return result

    async def read_resource(self, uri: str) -> str:
        """Read a resource by its URI scheme."""
        if not self._session:
            raise ConnectionError(f"MCPClient '{self.name}' is not connected.")

        result = await self._session.read_resource(uri)
        if hasattr(result, "contents") and result.contents:
            return result.contents[0].content
        return str(result)

    async def list_tools(self) -> List[str]:
        """Return list of discovered tool names."""
        if not self._session:
            raise ConnectionError(f"MCPClient '{self.name}' is not connected.")
        tools_result = await self._session.list_tools()
        self.tools = {t.name: t for t in tools_result.tools}
        return list(self.tools.keys())

    async def list_resources(self) -> List[str]:
        """Return list of discovered resource URIs."""
        if not self._session:
            raise ConnectionError(f"MCPClient '{self.name}' is not connected.")
        res = await self._session.list_resources()
        self.resources = res.resources
        return [r.uri for r in self.resources]


class MultiMCPManager:
    """
    Manages connections to multiple distinct MCP servers, providing unified
    tool dispatching and resource routing for agentic workflows.
    """

    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}

    def register_server(self, name: str, script_path: str, python_path: Optional[str] = None):
        """Register a server configuration."""
        self.clients[name] = MCPClient(name, script_path, python_path)

    async def connect_all(self):
        """Connect to all registered MCP servers concurrently."""
        for client in self.clients.values():
            await client.connect()

    async def disconnect_all(self):
        """Disconnect all active MCP clients."""
        for client in self.clients.values():
            await client.disconnect()

    async def __aenter__(self):
        await self.connect_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect_all()

    async def call_tool(self, server_name: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a specific tool on a specified server."""
        if server_name not in self.clients:
            raise KeyError(f"Server '{server_name}' not registered in MultiMCPManager.")
        return await self.clients[server_name].call_tool(tool_name, arguments)

    async def read_resource(self, uri: str) -> str:
        """
        Intelligently routes resource requests based on URI protocol scheme:
        - resume:// or job:// -> filesystem server
        - market:// or registry:// -> market intelligence server
        """
        if uri.startswith("market://") or uri.startswith("registry://"):
            server = self.clients.get("market") or self.clients.get("secondary")
        else:
            server = self.clients.get("filesystem")

        if not server:
            raise RuntimeError(f"No appropriate MCP server registered to handle URI: '{uri}'")

        return await server.read_resource(uri)


# ============================================================================
# Quick Verification Entrypoint
# ============================================================================

async def _verify_multi_mcp():
    print("Testing MultiMCPManager with primary and secondary servers...")
    manager = MultiMCPManager()
    manager.register_server("filesystem", "filesystem_mcp_server.py")
    manager.register_server("market", "secondary_mcp_server.py")

    async with manager:
        print("\n[Filesystem MCP Tools]:", await manager.clients["filesystem"].list_tools())
        print("[Market MCP Tools]:    ", await manager.clients["market"].list_tools())

        # Call filesystem tool
        batch = await manager.call_tool("filesystem", "batch_process", {"directory_path": "data/resumes"})
        print(f"\nFilesystem batch_process: {batch.get('processed_count')} candidates parsed.")

        # Call market intelligence tool
        bench = await manager.call_tool("market", "benchmark_market_role", {"role_title": "Senior AI Engineer"})
        print(f"Market benchmark salary:  ${bench.get('benchmark', {}).get('median_salary_usd', 0):,}")

    print("\nMultiMCPManager verification completed successfully!")


if __name__ == "__main__":
    asyncio.run(_verify_multi_mcp())
