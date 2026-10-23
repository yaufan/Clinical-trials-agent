"""Run the regulatory RAG MCP server.

python -m mcp_regulatory_rag                        # stdio
python -m mcp_regulatory_rag --transport streamable-http --host 0.0.0.0 --port 8105
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="mcp-regulatory-rag")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8105)
    args = parser.parse_args()

    from .server import server

    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            stateless_http=True,
            json_response=True,
        )


if __name__ == "__main__":
    main()
