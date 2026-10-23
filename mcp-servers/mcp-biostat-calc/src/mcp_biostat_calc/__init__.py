"""mcp-biostat-calc: deterministic biostatistics for AI-SaMD clinical study design.

All numerical work lives in :mod:`mcp_biostat_calc.core` as pure functions so it can be
unit-tested and reused without an MCP transport. :mod:`mcp_biostat_calc.server` wraps
those functions as MCP tools.
"""

__version__ = "0.1.0"
