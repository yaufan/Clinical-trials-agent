"""mcp-pubmed-evidence: PubMed (NCBI E-utilities) evidence retrieval for AI-SaMD protocols.

The package is split into transport-free building blocks so each can be unit tested:

* :mod:`mcp_pubmed_evidence.eutils`    – async E-utilities client with rate limiting
* :mod:`mcp_pubmed_evidence.queries`   – deterministic PubMed query builders
* :mod:`mcp_pubmed_evidence.extract`   – regex extraction of performance metrics from abstracts
* :mod:`mcp_pubmed_evidence.citations` – Vancouver / APA reference formatting
* :mod:`mcp_pubmed_evidence.server`    – the MCP tool surface
"""

__version__ = "0.1.0"
