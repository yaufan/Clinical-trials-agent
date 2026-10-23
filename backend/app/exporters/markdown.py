"""Assemble the full protocol document as Markdown."""

from __future__ import annotations

from ..schemas.protocol_input import ProtocolInput
from ..schemas.run import RunState


def _synopsis_table(inp: ProtocolInput, state: RunState) -> str:
    dp, ai, sd, sa = (
        inp.device_profile,
        inp.ai_specifications,
        inp.study_design,
        inp.statistical_assumptions,
    )
    n = (state.sap.final_sample_size if state.sap else {}) or {}
    rows = [
        ("Device / 試驗醫材", f"{dp.device_name} {dp.version} ({dp.samd_category.value})"),
        (
            "Intended use / 預期用途",
            f"{dp.indications_for_use.target_disease}; {dp.indications_for_use.target_population}; {dp.indications_for_use.clinical_setting}",
        ),
        ("Jurisdictions / 目標市場", ", ".join(j.value for j in dp.target_jurisdictions)),
        (
            "Algorithm / 演算法",
            f"{ai.algorithm_type.value}; input {ai.input_modality}; output {', '.join(o.value for o in ai.output_format)}; workflow {ai.human_ai_workflow.value}",
        ),
        (
            "Design / 試驗設計",
            f"{sd.design_type.value}, {sd.data_collection_mode.value}, {sd.study_sites_count} site(s), sampling {sd.sampling_strategy.value}",
        ),
        (
            "Reference standard / 參考標準",
            f"{sd.ground_truth_method.reference_standard_type.value}: {sd.ground_truth_method.panel_details or ''}",
        ),
        (
            "Primary endpoints / 主要指標",
            ", ".join(e.value for e in sa.primary_endpoints) + f" ({sa.hypothesis_type.value})",
        ),
        (
            "Sample size / 樣本數",
            ", ".join(f"{k}={v}" for k, v in n.items() if v is not None) or "see SAP",
        ),
        (
            "α / power",
            f"{sa.alpha} ({sa.alpha_sidedness}) / {sa.power}; attrition {sa.expected_attrition_rate}",
        ),
    ]
    out = ["| Item | Value |", "|---|---|"]
    out += [f"| {k} | {str(v).replace('|', '/')} |" for k, v in rows]
    return "\n".join(out)


def render_protocol_markdown(inp: ProtocolInput, state: RunState) -> str:
    dp = inp.device_profile
    meta = inp.project_meta
    lines: list[str] = []
    lines.append(f"# Clinical Investigation Plan — {dp.device_name} {dp.version}")
    lines.append(f"# 臨床試驗計畫書 — {dp.device_name} {dp.version}")
    lines.append("")
    lines.append(f"**Protocol ID:** {meta.protocol_id or '[TO BE ASSIGNED]'}  ")
    lines.append(f"**Sponsor:** {meta.sponsor or '[TO BE CONFIRMED]'}  ")
    lines.append(
        f"**Principal Investigator:** {meta.principal_investigator or '[TO BE CONFIRMED]'}  "
    )
    lines.append(
        f"**Draft generated:** {state.updated_at:%Y-%m-%d} · run `{state.run_id}` · stage `{state.stage.value}`"
    )
    lines.append("")
    lines.append(
        "> ⚠️ AI-assisted draft. Every statement must be verified by the sponsor's regulatory, clinical and biostatistics leads before IRB/TFDA/FDA submission. Items marked **[TO BE CONFIRMED]** are unresolved."
    )
    lines.append("")
    lines.append("## Synopsis Table / 摘要表")
    lines.append(_synopsis_table(inp, state))
    lines.append("")
    if state.triage:
        lines.append("## Regulatory Triage Summary / 法規路徑摘要")
        lines.append(f"- **Study archetype:** {state.triage.study_archetype}")
        for p in state.triage.regulatory_pathways:
            lines.append(f"- **Pathway:** {p}")
        lines.append(f"- **Risk assessment:** {state.triage.significant_risk_assessment}")
        lines.append(
            "- **Applicable checklists:** "
            + ", ".join(
                f"{c.get('checklist_id')} ({c.get('role')})"
                for c in state.triage.applicable_checklists
            )
        )
        lines.append("")
    for sec in state.sections:
        lines.append(f"## {sec.title_zh} / {sec.title_en}")
        lines.append(sec.markdown.strip())
        if sec.open_questions:
            lines.append("")
            lines.append("**Open questions / 待確認事項:**")
            lines += [f"- [TO BE CONFIRMED] {q}" for q in sec.open_questions]
        lines.append("")
    if state.sap and state.sap.computations:
        lines.append("## Appendix A — Sample Size Computations / 附錄 A 樣本數計算紀錄")
        for i, c in enumerate(state.sap.computations, 1):
            lines.append(f"### A.{i} `{c.tool}`")
            lines.append(f"{c.interpretation}")
            lines.append("")
            lines.append("Inputs: `" + ", ".join(f"{k}={v}" for k, v in c.inputs.items()) + "`")
            keep = {k: v for k, v in c.outputs.items() if not isinstance(v, dict | list)}
            lines.append("Outputs: `" + ", ".join(f"{k}={v}" for k, v in keep.items()) + "`")
            lines.append("")
    if state.evidence:
        lines.append("## Appendix B — Evidence Register / 附錄 B 實證清單")
        lines.append("| Source | Ref | Title | Design | n | Readers | Accepted |")
        lines.append("|---|---|---|---|---|---|---|")
        for it in state.evidence.items:
            lines.append(
                f"| {it.source} | {it.ref_id} | {it.title[:80].replace('|', '/')} | {(it.design or '')[:40].replace('|', '/')} | {it.sample_size or ''} | {it.readers or ''} | {'✓' if it.accepted else '✗'} |"
            )
        lines.append("")
    if state.audits:
        a = state.audits[-1]
        lines.append(
            f"## Appendix C — Compliance Audit (iteration {a.iteration}) / 附錄 C 合規審查"
        )
        lines.append(
            f"Checklists: {', '.join(a.checklists_audited)} · pass {a.n_pass} · partial {a.n_partial} · fail {a.n_fail} · N/A {a.n_not_applicable} · verdict **{a.overall_verdict}**"
        )
        lines.append("")
        lines.append("| Checklist | Item | Status | Finding |")
        lines.append("|---|---|---|---|")
        for r in a.items:
            lines.append(
                f"| {r.checklist_id} | {r.item_id} | {r.status} | {r.finding[:160].replace('|', '/')} |"
            )
        lines.append("")
    cites = sorted({c for s in state.sections for c in s.citations})
    if cites:
        lines.append("## References / 參考文獻")
        lines += [f"{i}. {c}" for i, c in enumerate(cites, 1)]
        lines.append("")
    if state.warnings:
        lines.append("## Generation Warnings / 產生過程警示")
        lines += [f"- {w}" for w in state.warnings]
    return "\n".join(lines)
