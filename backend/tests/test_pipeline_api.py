import io
import zipfile

import pytest

from app.schemas.run import RunStage


async def _create_and_start(client, example_input):
    r = await client.post("/api/projects", json={"name": "Demo", "input": example_input})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    r = await client.post(f"/api/projects/{pid}/runs")
    assert r.status_code == 201, r.text
    return pid, r.json()["run_id"]


@pytest.mark.anyio
async def test_meta_endpoints(client):
    assert (await client.get("/api/health")).json()["status"] == "ok"
    schema = (await client.get("/api/meta/schema")).json()
    assert "device_profile" in schema["properties"]
    assert (await client.get("/api/meta/example")).json()["device_profile"]["device_name"]
    cfg = (await client.get("/api/meta/config")).json()
    assert cfg["llm_provider"] == "fake"
    health = (await client.get("/api/meta/mcp-health")).json()
    assert health["biostat"]["ok"] and health["regulatory_rag"]["ok"]


@pytest.mark.anyio
async def test_project_validation_error(client, example_input):
    bad = {
        **example_input,
        "statistical_assumptions": {**example_input["statistical_assumptions"], "alpha": 1.5},
    }
    r = await client.post("/api/projects", json={"name": "Bad", "input": bad})
    assert r.status_code == 422


@pytest.mark.anyio
async def test_full_pipeline_with_hitl_gate_and_exports(app, client, example_input, fake_llm):
    pid, run_id = await _create_and_start(client, example_input)
    mgr = app.state.manager
    state = await mgr.wait(run_id, max_seconds=60)
    assert state.stage == RunStage.awaiting_evidence_confirmation, state.error
    assert state.triage and state.triage.study_archetype == "standalone_diagnostic_accuracy"
    assert {c["checklist_id"] for c in state.triage.applicable_checklists} >= {
        "STARD-AI",
        "TFDA-AIML-SaMD",
        "ISO14155-CIP",
    }
    assert state.evidence and len(state.evidence.items) >= 5
    sources = {i.source for i in state.evidence.items}
    assert {"clinicaltrials", "openfda", "pubmed", "regulatory_rag"} <= sources

    # premature confirmation of a wrong stage is rejected
    r = await client.put(f"/api/runs/{run_id}/sections/synopsis", json={"markdown": "x"})
    assert r.status_code == 404  # no sections yet

    # confirm: drop one predicate, add a baseline override
    r = await client.post(
        f"/api/runs/{run_id}/confirm-evidence",
        json={
            "accepted_ref_ids": [i.ref_id for i in state.evidence.items if i.ref_id != "K193456"],
            "reviewer_notes": "looks good",
            "baseline_overrides": {"unaided_reader_sensitivity": 0.84},
        },
    )
    assert r.status_code == 200, r.text
    state = await mgr.wait(run_id, max_seconds=120)
    assert state.stage == RunStage.completed, (state.error, state.warnings)
    assert (
        state.evidence.confirmed
        and state.evidence.baseline_performance["unaided_reader_sensitivity"] == 0.84
    )
    assert not any(i.accepted for i in state.evidence.items if i.ref_id == "K193456")

    # SAP: deterministic biostat numbers came from the real MCP server
    assert state.sap is not None
    tools = [c.tool for c in state.sap.computations]
    assert (
        "calc_standalone_sample_size" in tools
        and "calc_buderer_sample_size" in tools
        and "allocate_strata" in tools
    )
    assert state.sap.final_sample_size["n_total"] > 0
    assert (
        sum(state.sap.stratified_allocation["by_site"].values())
        == state.sap.final_sample_size["n_total"]
    )

    # sections & audit
    assert [s.key for s in state.sections] == [
        "synopsis",
        "background",
        "objectives",
        "device",
        "design",
        "eligibility",
        "ground_truth",
        "statistics",
        "data_management",
        "ethics",
    ]
    assert (
        state.audits
        and state.audits[-1].n_pass
        + state.audits[-1].n_partial
        + state.audits[-1].n_fail
        + state.audits[-1].n_not_applicable
        >= 30
    )
    assert state.llm_calls >= 14 and state.tool_calls >= 10

    # second confirmation is rejected (409)
    r = await client.post(f"/api/runs/{run_id}/confirm-evidence", json={})
    assert r.status_code == 409

    # events were persisted
    events = (await client.get(f"/api/runs/{run_id}/events/history")).json()
    types = {e["type"] for e in events}
    assert {"stage_started", "stage_completed", "hitl_required", "tool_call"} <= types
    tool_events = [e for e in events if e["type"] == "tool_call"]
    failed = [
        f"{e['data']['server']}.{e['data']['tool']}" for e in tool_events if not e["data"].get("ok")
    ]
    assert state.tool_calls == len(tool_events), (state.tool_calls, len(tool_events), failed)

    # edit a section
    r = await client.put(
        f"/api/runs/{run_id}/sections/synopsis", json={"markdown": "## edited", "editor": "tester"}
    )
    assert r.status_code == 200 and r.json()["sections"][0]["markdown"] == "## edited"

    # exports
    md = await client.get(f"/api/runs/{run_id}/export.md")
    assert (
        md.status_code == 200
        and "Clinical Investigation Plan" in md.text
        and "Appendix A" in md.text
    )
    docx = await client.get(f"/api/runs/{run_id}/export.docx")
    assert docx.status_code == 200
    with zipfile.ZipFile(io.BytesIO(docx.content)) as z:
        assert "word/document.xml" in z.namelist()

    # project listing shows latest run
    projects = (await client.get("/api/projects")).json()
    assert projects[0]["latest_run"]["stage"] == "completed"


@pytest.mark.anyio
async def test_audit_revision_loop(app, client, example_input, fake_llm):
    """First audit fails two items → writer revises → second audit passes."""
    calls = {"audit": 0}

    def auditor(system, messages, schema):
        calls["audit"] += 1
        import json as _json

        items = _json.loads(
            messages[0].content.split("CHECKLIST ITEMS TO JUDGE:\n", 1)[1].split("\n\nReturn", 1)[0]
        )
        status = "fail" if calls["audit"] <= 3 else "pass"
        return {
            "judgements": [
                {
                    "item_id": it["item_id"],
                    "status": status,
                    "evidence_sections": [],
                    "finding": "f",
                    "fix_suggestion": "add it" if status == "fail" else None,
                    "target_section_key": "device",
                }
                for it in items
            ]
        }

    fake_llm.overrides["Compliance Auditor Agent"] = auditor
    pid, run_id = await _create_and_start(client, example_input)
    mgr = app.state.manager
    await mgr.wait(run_id, max_seconds=60)
    r = await client.post(f"/api/runs/{run_id}/confirm-evidence", json={})
    assert r.status_code == 200
    state = await mgr.wait(run_id, max_seconds=120)
    assert state.stage == RunStage.completed, state.error
    assert len(state.audits) == 2
    assert state.audits[0].n_fail > 0 and state.audits[0].revision_requests
    assert state.section("device").revision == 2
    assert state.section("device").last_edited_by.startswith("writer_agent")


@pytest.mark.anyio
async def test_cancel_run(app, client, example_input):
    pid, run_id = await _create_and_start(client, example_input)
    r = await client.post(f"/api/runs/{run_id}/cancel")
    assert r.status_code == 200
    assert r.json()["stage"] in ("cancelled", "awaiting_evidence_confirmation", "completed")


@pytest.mark.anyio
async def test_failed_section_and_revision_do_not_fail_the_run(
    app, client, example_input, fake_llm
):
    """A section whose generation blows up becomes a placeholder; the run still completes."""
    from app.llm.base import LLMTruncated

    def boom(system, messages, schema):
        raise LLMTruncated("finish_reason=length")

    fake_llm.overrides[r"SECTION TO WRITE: 試驗醫材描述"] = boom
    pid, run_id = await _create_and_start(client, example_input)
    mgr = app.state.manager
    await mgr.wait(run_id, max_seconds=60)
    assert (await client.post(f"/api/runs/{run_id}/confirm-evidence", json={})).status_code == 200
    state = await mgr.wait(run_id, max_seconds=120)
    assert state.stage == RunStage.completed, state.error
    device = state.section("device")
    assert device.last_edited_by == "writer_agent(failed)" and "[TO BE CONFIRMED" in device.markdown
    assert any("could not be generated" in w for w in state.warnings)
    assert len(state.sections) == 10


def test_harvester_query_simplification():
    from app.agents.harvester import disease_acronym, simplify_disease, simplify_modality

    assert (
        simplify_disease("Acute intracranial hemorrhage (ICH)") == "Acute intracranial hemorrhage"
    )
    assert disease_acronym("Acute intracranial hemorrhage (ICH)") == "ICH"
    assert simplify_modality("Non-contrast head CT (DICOM)") == "CT"
    assert simplify_modality("Digital breast tomosynthesis") == "tomosynthesis"
    assert simplify_modality("12-lead ECG waveform") == "ECG"
    assert simplify_modality("structured EHR tables") == "electronic health records"
    assert simplify_modality("proprietary sensor stream") is None


@pytest.mark.anyio
async def test_harvest_falls_back_to_broader_queries(app, client, example_input):
    """Modality-qualified searches return nothing → retried without modality → then by acronym."""
    mgr = app.state.manager
    ct = mgr.mcp.targets["clinicaltrials"]
    calls: list[dict] = []
    full = ct.responses["search_samd_trials"]

    def search(args):
        calls.append(args)
        if "modality" in args:
            return {"total_count": 0, "returned": 0, "studies": []}
        return full

    ct.responses["search_samd_trials"] = search
    pid, run_id = await _create_and_start(client, example_input)
    state = await mgr.wait(run_id, max_seconds=60)
    assert state.stage == RunStage.awaiting_evidence_confirmation, state.error
    assert calls[0] == {
        "condition": "Acute intracranial hemorrhage",
        "page_size": 15,
        "modality": "CT",
    }
    assert "modality" not in calls[1] and calls[1]["condition"] == "Acute intracranial hemorrhage"
    assert any(i.source == "clinicaltrials" for i in state.evidence.items)


@pytest.mark.anyio
async def test_api_key_enforced_when_configured(tmp_path, fake_llm, mcp_factory):
    from httpx import ASGITransport, AsyncClient

    from app.config import Settings
    from app.db import Database
    from app.main import create_app

    settings = Settings(
        llm_provider="fake", database_url=f"sqlite+aiosqlite:///{tmp_path}/k.db", api_key="s3cret"
    )
    db = Database(settings.database_url)
    await db.init()
    application = create_app(settings, llm=fake_llm, mcp=mcp_factory(), database=db)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as c:
            assert (await c.get("/api/health")).status_code == 200  # exempt
            assert (await c.get("/api/meta/example")).status_code == 401
            assert (
                await c.get("/api/meta/example", headers={"X-API-Key": "wrong"})
            ).status_code == 401
            assert (
                await c.get("/api/meta/example", headers={"X-API-Key": "s3cret"})
            ).status_code == 200
            assert (
                await c.get("/api/meta/example", headers={"Authorization": "Bearer s3cret"})
            ).status_code == 200
            assert (
                await c.options(
                    "/api/meta/example",
                    headers={
                        "Origin": "http://localhost:3000",
                        "Access-Control-Request-Method": "GET",
                    },
                )
            ).status_code in (200, 204)
    finally:
        await application.state.manager.shutdown()
        await db.close()
