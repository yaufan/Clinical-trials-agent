from mcp_regulatory_rag import checklists as ck


def test_all_checklists_load_and_have_items():
    all_ = ck.load_all()
    assert {
        "SPIRIT-AI",
        "STARD-AI",
        "CONSORT-AI",
        "ISO14155-CIP",
        "TFDA-AIML-SaMD",
        "FDA-CADe",
        "IMDRF-N41",
        "TRIPOD-AI",
    } <= set(all_)
    assert len(all_["SPIRIT-AI"].items) == 15
    ids = [i.id for i in all_["SPIRIT-AI"].items]
    assert ids.count("11a(i)") == 1 and "10(ii)" in ids and "29(ii)" in ids
    for cl in all_.values():
        assert all(it.text and it.keywords for it in cl.items), cl.id


def test_get_checklist_is_case_insensitive():
    assert ck.get_checklist("spirit_ai").id == "SPIRIT-AI"


def test_select_checklists_standalone_is_stard_not_spirit_primary():
    sel = ck.select_checklists("Standalone_Performance", "CADe", ["TFDA", "US_FDA_510k"])
    roles = {s.checklist_id: s.role for s in sel}
    assert roles["STARD-AI"] == "primary"
    assert roles["SPIRIT-AI"] == "supporting"
    assert roles["TFDA-AIML-SaMD"] == "primary"
    assert "FDA-CADe" in roles and "ISO14155-CIP" in roles


def test_select_checklists_rct_is_spirit_primary():
    sel = ck.select_checklists("Prospective_Interventional_RCT", "CADt", ["CE_MDR"])
    roles = {s.checklist_id: s.role for s in sel}
    assert roles["SPIRIT-AI"] == "primary"
    assert "STARD-AI" not in roles
    assert "TFDA-AIML-SaMD" not in roles
    assert roles["CONSORT-AI"] == "supporting"


def test_select_checklists_prognostic_adds_tripod():
    sel = ck.select_checklists("Standalone_Performance", "Prognostic_Predictive", [])
    assert sel[0].checklist_id == "TRIPOD-AI"


def test_prescreen_coverage_flags_missing_and_covered():
    sections = {
        "Device Description": "NeuroDetect-CT AI v2.1.0 (locked algorithm, software version 2.1.0) outputs a bounding box and a probability score. Input: non-contrast head CT DICOM, slice thickness ≤ 5 mm; low quality studies with severe motion artefact are excluded.",
        "Statistical Analysis": "Sensitivity and specificity will be estimated with 95% CI.",
    }
    rep = ck.prescreen_coverage("SPIRIT-AI", sections)
    by_id = {i.item_id: i for i in rep.items}
    assert by_id["11a(i)"].status == "likely_covered"  # version keywords
    assert by_id["11a(v)"].status == "likely_covered"  # output keywords
    assert by_id["29(ii)"].status == "missing"  # code access never mentioned
    assert rep.n_items == 15
    assert rep.n_likely_covered + rep.n_weak + rep.n_missing == 15


def test_prescreen_matches_chinese_keywords():
    rep = ck.prescreen_coverage(
        "TFDA-AIML-SaMD", {"資料": "本研究將進行去識別化處理並遵循個資法及人體研究法。"}
    )
    tw10 = next(i for i in rep.items if i.item_id == "TW-10")
    assert tw10.status == "likely_covered"
    assert "去識別化" in tw10.matched_keywords
