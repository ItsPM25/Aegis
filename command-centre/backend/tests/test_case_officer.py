"""Case Officer tests — the dossier must be exact; the template brief must never die."""

from aegis_command.case_officer import _template_case_file, build_dossier

SCAM = {
    "event_id": "scam_1", "raw_text": "This is Inspector Sharma from CBI, FIR registered against your Aadhaar money laundering",
    "verdict": "scam", "scam_type": "digital_arrest", "risk_score": 0.97,
    "phone_number": "+91-99999", "timestamp": "2026-07-07T10:00:00Z",
    "location_hint": {"district": "Jamtara", "lat": 23.96, "lon": 86.80},
}
NOTE = {
    "event_id": "note_1", "denomination": "500", "verdict": "fake",
    "missing_features": ["security_thread"], "timestamp": "2026-07-08T10:00:00Z",
    "location_hint": {"district": "Jamtara", "lat": 23.95, "lon": 86.81},
}
GRAPH = {"rings": [{"ring_id": "ring_9", "district": "Jamtara", "label": "layering chain", "size": 4, "total_amount": 100000}]}


def test_dossier_gathers_only_district_evidence():
    d = build_dossier("Jamtara", [SCAM], [NOTE], GRAPH)
    assert d["counts"] == {"scams": 1, "fake_notes": 1, "rings": 1, "ring_accounts": 4}
    other = build_dossier("Alwar", [SCAM], [NOTE], GRAPH)
    assert other["counts"]["scams"] == 0 and other["counts"]["rings"] == 0


def test_dossier_timeline_is_chronological_with_refs():
    d = build_dossier("Jamtara", [SCAM], [NOTE], GRAPH)
    assert [e["ref"] for e in d["timeline"]] == ["scam_1", "note_1"]


def test_template_brief_cites_evidence_and_hedges():
    d = build_dossier("Jamtara", [SCAM], [NOTE], GRAPH)
    brief = _template_case_file(d)
    assert "Jamtara" in brief["summary"]
    assert "hypothesis" in brief and "not proof" in brief["hypothesis"]
    assert any("freeze" in a.lower() or "bank" in a.lower() for a in brief["recommended_actions"])
    assert brief["timeline"]  # refs preserved
    assert "[scam_1]" in brief["timeline"][0]


def test_template_brief_handles_empty_district():
    d = build_dossier("Nowhere", [], [], None)
    brief = _template_case_file(d)
    assert "no direct events" in brief["summary"]
    assert brief["recommended_actions"]  # still actionable ("continue monitoring")
