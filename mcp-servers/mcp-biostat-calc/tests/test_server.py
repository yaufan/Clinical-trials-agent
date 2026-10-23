"""In-process MCP round-trip through the official client (no sockets)."""

import pytest
from mcp.client.client import Client

from mcp_biostat_calc.server import server


@pytest.mark.anyio
async def test_tools_are_listed_with_schemas():
    async with Client(server) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools.tools}
        assert {
            "calc_standalone_sample_size",
            "calc_mrmc_sample_size",
            "calc_buderer_sample_size",
        } <= names
        standalone = next(t for t in tools.tools if t.name == "calc_standalone_sample_size")
        assert "expected_sensitivity" in standalone.input_schema["properties"]
        assert standalone.output_schema is not None


@pytest.mark.anyio
async def test_call_standalone_tool_returns_structured_content():
    async with Client(server) as client:
        result = await client.call_tool(
            "calc_standalone_sample_size",
            {
                "expected_sensitivity": 0.92,
                "sensitivity_goal": 0.82,
                "expected_specificity": 0.90,
                "specificity_goal": 0.80,
                "prevalence": 0.2,
            },
        )
        assert not result.is_error
        sc = result.structured_content
        assert sc["n_positive"] > 0 and sc["n_negative"] > 0
        assert sc["n_total_with_attrition"] >= sc["n_total"]


@pytest.mark.anyio
async def test_invalid_input_surfaces_as_tool_error():
    async with Client(server) as client:
        result = await client.call_tool("calc_one_sample_proportion", {"p0": 0.5, "p1": 0.5})
        assert result.is_error
