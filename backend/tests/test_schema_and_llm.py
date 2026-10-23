import httpx
import pytest
import respx

from app.llm.base import LLMMessage, extract_json, strip_reasoning
from app.llm.fake import FakeLLM, fill_schema
from app.llm.openai_compat import OpenAICompatibleLLM
from app.schemas.protocol_input import EXAMPLE_INPUT, ProtocolInput
from app.schemas.run import AuditReport, EvidenceMatrix, StatisticalAnalysisPlan, TriageDecision


def test_example_input_validates_and_schema_has_enums():
    p = ProtocolInput.model_validate(EXAMPLE_INPUT)
    assert p.device_profile.samd_category.value == "CADt"
    schema = ProtocolInput.model_json_schema()
    assert "DesignType" in schema["$defs"]
    assert set(schema["$defs"]["DesignType"]["enum"]) >= {
        "Standalone_Performance",
        "MRMC_Reader_Study",
    }


def test_mrmc_requires_config():
    bad = {
        **EXAMPLE_INPUT,
        "study_design": {**EXAMPLE_INPUT["study_design"], "design_type": "MRMC_Reader_Study"},
    }
    with pytest.raises(ValueError):
        ProtocolInput.model_validate(bad)


def test_goal_pairing_validation():
    bad = {
        **EXAMPLE_INPUT,
        "statistical_assumptions": {
            **EXAMPLE_INPUT["statistical_assumptions"],
            "sensitivity_goal": None,
        },
    }
    with pytest.raises(ValueError):
        ProtocolInput.model_validate(bad)


@pytest.mark.parametrize(
    "model", [TriageDecision, EvidenceMatrix, StatisticalAnalysisPlan, AuditReport]
)
def test_fill_schema_produces_valid_instances(model):
    model.model_validate(fill_schema(model.model_json_schema()))


def test_extract_json_handles_fences_and_reasoning():
    assert extract_json('<think>reasoning</think>Here: ```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('text before {"k": [1, {"n": "x}"}]} after') == {"k": [1, {"n": "x}"}]}
    assert strip_reasoning("<think>a</think> b") == "b"


@pytest.mark.anyio
async def test_fake_llm_routes_and_records():
    llm = FakeLLM(overrides={"Auditor": {"judgements": []}})
    r = await llm.complete(
        system="ROLE: Auditor", messages=[LLMMessage("user", "x")], json_schema={"type": "object"}
    )
    assert r.parsed == {"judgements": []}
    assert len(llm.calls) == 1


@pytest.mark.anyio
@respx.mock
async def test_openai_compat_json_schema_mode():
    route = respx.post("http://llm.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "m",
                "choices": [
                    {"message": {"content": '<think>hm</think>{"x": 1}'}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3},
            },
        )
    )
    llm = OpenAICompatibleLLM(base_url="http://llm.test/v1", model="m", timeout=5)
    r = await llm.complete(
        system="s", messages=[LLMMessage("user", "u")], json_schema={"type": "object", "title": "T"}
    )
    assert r.parsed == {"x": 1} and r.input_tokens == 5
    body = route.calls[0].request.content
    assert b'"response_format"' in body and b'"json_schema"' in body


@pytest.mark.anyio
@respx.mock
async def test_openai_compat_falls_back_when_schema_rejected():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        body = request.content.decode()
        if '"json_schema"' in body:
            return httpx.Response(400, json={"error": "response_format json_schema not supported"})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": 'Sure: {"ok": true}'}, "finish_reason": "stop"}]
            },
        )

    respx.post("http://llm.test/v1/chat/completions").mock(side_effect=handler)
    llm = OpenAICompatibleLLM(base_url="http://llm.test/v1", model="m", timeout=5)
    r = await llm.complete(
        system="s", messages=[LLMMessage("user", "u")], json_schema={"type": "object"}
    )
    assert r.parsed == {"ok": True}
    assert calls["n"] == 2
    # capability is remembered: next call goes straight to json_object mode
    await llm.complete(
        system="s", messages=[LLMMessage("user", "u")], json_schema={"type": "object"}
    )
    assert calls["n"] == 3


@pytest.mark.anyio
@respx.mock
async def test_openai_compat_retries_on_503(monkeypatch):
    import app.llm.openai_compat as mod

    async def no_sleep(_):
        return None

    monkeypatch.setattr(mod.asyncio, "sleep", no_sleep)
    respx.post("http://llm.test/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(
                200, json={"choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}]}
            ),
        ]
    )
    llm = OpenAICompatibleLLM(base_url="http://llm.test/v1", model="m", timeout=5)
    r = await llm.complete(system="s", messages=[LLMMessage("user", "u")])
    assert r.text == "hello"
