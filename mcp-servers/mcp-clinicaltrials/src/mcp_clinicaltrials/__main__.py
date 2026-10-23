"""Run the ClinicalTrials.gov MCP server.

python -m mcp_clinicaltrials                       # stdio (for local MCP hosts)
python -m mcp_clinicaltrials --transport streamable-http --host 0.0.0.0 --port 8102
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="mcp-clinicaltrials")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8102)
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
