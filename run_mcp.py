#!/usr/bin/env python3
"""
Runner para o servidor MCP do Agente USJ/CGE.

Uso:
  # Via stdio (padrão para integração com editores/IDEs):
  python run_mcp.py

  # Ou via FastMCP CLI:
  fastmcp run src/mcp_server.py

  # Ou como módulo:
  python -m src.mcp_server
"""

import sys
from pathlib import Path

# Garante que o projeto está no path
sys.path.insert(0, str(Path(__file__).parent))

from src.mcp_server import mcp

if __name__ == "__main__":
    mcp.run()
