import subprocess
import json
import sys
import os

class MCPClient:
    def __init__(self):    
        self.process = subprocess.Popen(
            [sys.executable, "app/mcp_server/server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._msg_id = 0
        # Send MCP initialize handshake
        self._initialize()

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    def _send(self, message: dict) -> None:
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def _read(self) -> dict:
        while True:
            line = self.process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                # Skip notifications, only return responses
                if "id" in msg:
                    return msg
            except json.JSONDecodeError:
                continue
        return {}

    def _initialize(self) -> None:
        self._send({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mcp-client", "version": "1.0"}
            }
        })
        self._read()
        # Send initialized notification
        self._send({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        })

    def list_tools(self) -> list:
        """Get list of all available tools from MCP server."""
        self._send({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {}
        })
        response = self._read()
        return response.get("result", {}).get("tools", [])

    def call_tool(self, tool_name: str, args: dict) -> dict:
        self._send({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args
            }
        })
        return self._read()

    def _close(self):
        self.process.terminate()