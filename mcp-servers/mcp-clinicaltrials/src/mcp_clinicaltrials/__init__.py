"""mcp-clinicaltrials: ClinicalTrials.gov API v2 as MCP tools.

:mod:`client` talks to the REST API, :mod:`models` normalises the deeply nested
``protocolSection`` into flat pydantic models, :mod:`analysis` derives deterministic design
statistics, and :mod:`server` exposes everything as MCP tools.
"""

__version__ = "0.1.0"
