"""Fusion layer tests — correlation correctness + contract compliance."""

import json

import pytest

from aegis_fusion.correlator import correlate
from aegis_fusion.fuse import SAMPLES, fuse, validate_against_contract


@pytest.fixture()
def sample_signals():
    scam = json.loads((SAMPLES / "scam_detection.sample.json").read_text(encoding="utf-8"))
    note = json.loads((SAMPLES / "counterfeit.sample.json").read_text(encoding="utf-8"))
    graph = json.loads((SAMPLES / "fraud_graph.sample.json").read_text(encoding="utf-8"))
    return [scam], [note], graph


def test_samples_correlate_to_critical(sample_signals):
    """The bundled samples are all in Jamtara within 90 minutes — the engine
    must link all three domains and flag a critical coordinated hub."""
    scams, notes, graph = sample_signals
    c = correlate(scams, notes, graph)
    assert c.threat_level == "critical"
    domains = {l.type for l in c.linked_signals}
    assert domains == {"scam", "counterfeit", "fraud_ring"}
    assert "shared_district" in c.correlation_basis
    assert "geospatial_overlap" in c.correlation_basis
    assert "temporal_proximity" in c.correlation_basis


def test_isolated_signals_stay_low():
    """Signals in different districts, far apart in time -> no links."""
    scam = {
        "event_id": "s1", "verdict": "scam", "risk_score": 0.9,
        "timestamp": "2026-07-01T00:00:00Z",
        "location_hint": {"district": "Chennai Central", "lat": 13.08, "lon": 80.27},
    }
    note = {
        "event_id": "n1", "verdict": "fake", "confidence": 0.9,
        "timestamp": "2026-07-30T00:00:00Z",
        "location_hint": {"district": "Mumbai South", "lat": 18.93, "lon": 72.83},
    }
    c = correlate([scam], [note], {"rings": []})
    assert c.linked_signals == []
    assert c.threat_level == "medium"  # signals exist but are unlinked


def test_no_signals_is_low():
    c = correlate([], [], {"rings": []})
    assert c.threat_level == "low"
    assert c.linked_signals == []


def test_legit_signals_never_link():
    """verdict=legit / genuine must be excluded from correlation entirely —
    false positives on citizens are the one unforgivable failure mode."""
    scam = {
        "event_id": "s1", "verdict": "legit", "risk_score": 0.05,
        "timestamp": "2026-07-07T10:00:00Z",
        "location_hint": {"district": "Jamtara", "lat": 23.79, "lon": 86.80},
    }
    note = {
        "event_id": "n1", "verdict": "genuine", "confidence": 0.95,
        "timestamp": "2026-07-07T10:30:00Z",
        "location_hint": {"district": "Jamtara", "lat": 23.79, "lon": 86.80},
    }
    c = correlate([scam], [note], {"rings": [{"ring_id": "r1", "account_ids": [],
                                              "risk_score": 0.9, "district": "Jamtara"}]})
    assert all(l.type != "scam" for l in c.linked_signals)
    assert all(l.type != "counterfeit" for l in c.linked_signals)


def _trail_world(**scam_overrides):
    """A scam with reported_payment + a hub ring whose collector received a
    matching inflow. Overrides let each test break exactly one condition."""
    scam = {
        "event_id": "s_pay", "verdict": "scam", "risk_score": 0.99,
        "timestamp": "2026-06-24T10:00:00Z",
        "location_hint": {"district": "Alwar", "lat": 27.55, "lon": 76.63},
        "reported_payment": {"amount": 49_999, "method": "upi"},
    }
    scam.update(scam_overrides)
    graph = {
        "rings": [{
            "ring_id": "ring_x", "account_ids": ["collector", "mule_1"],
            "risk_score": 0.99, "size": 2, "label": "mule collection hub",
            "district": "Alwar",
        }],
        "edges": [
            # the traced inflow: victim -> collector, matching amount, 6h later
            {"source": "victim_7", "target": "collector", "amount": 49_999.0,
             "timestamp": "2026-06-24T16:04:22+00:00"},
            # intra-ring forward (must never be treated as an inflow)
            {"source": "collector", "target": "mule_1", "amount": 620_000.0,
             "timestamp": "2026-06-27T10:00:00+00:00"},
        ],
    }
    return scam, graph


def test_money_trail_traced():
    """Amount + window match (same district too, here) -> shared_account link."""
    scam, graph = _trail_world()
    c = correlate([scam], [], graph)
    assert "shared_account" in c.correlation_basis
    assert "shared_district" in c.correlation_basis  # bonus signal, both in Alwar
    assert c.money_trails == [{
        "scam_event_id": "s_pay", "ring_id": "ring_x",
        "account_id": "collector", "amount": 49_999.0, "district": "Alwar",
    }]
    assert any("traced into" in l.reason for l in c.linked_signals)
    assert any(l.get("kind") == "scam-ring-payment" for l in c.facts["links"])


def test_money_trail_traced_across_districts():
    """Real mule rings usually operate far from their victims by design — the
    money trail must fire on amount + timing ALONE, with no district match.
    This is the fix for the case where district would wrongly gate a real trail."""
    scam, graph = _trail_world(
        location_hint={"district": "Kerala Coast", "lat": 9.98, "lon": 76.28}
    )
    c = correlate([scam], [], graph)  # ring is in Alwar, victim is in Kerala
    assert "shared_account" in c.correlation_basis
    assert "shared_district" not in c.correlation_basis  # correctly did NOT match
    assert c.money_trails == [{
        "scam_event_id": "s_pay", "ring_id": "ring_x",
        "account_id": "collector", "amount": 49_999.0, "district": "Alwar",
    }]


@pytest.mark.parametrize(
    "overrides",
    [
        {"reported_payment": None},  # no payment reported
        {"reported_payment": {"amount": 25_000}},  # amount mismatch
        {"timestamp": "2026-06-30T10:00:00Z"},  # payment BEFORE the call
        {"timestamp": "2026-06-10T10:00:00Z"},  # payment > 96h after the call
    ],
)
def test_money_trail_requires_amount_and_timing(overrides):
    scam, graph = _trail_world(**overrides)
    c = correlate([scam], [], graph)
    assert c.money_trails == []
    assert "shared_account" not in c.correlation_basis


def test_fusion_output_matches_contract(sample_signals):
    """End-to-end: fuse() output must validate against the shared schema."""
    scams, notes, graph = sample_signals
    out = fuse(scams, notes, graph)
    payload = json.loads(out.model_dump_json())
    validate_against_contract(payload)  # raises on violation
    assert payload["schema_version"] == "1.0"
    assert payload["audit_trail"]["inputs_hash"]
    assert len(payload["recommended_actions"]) >= 2


def test_audit_hash_is_reproducible(sample_signals):
    """Same inputs -> same inputs_hash. This is the legal-admissibility anchor."""
    scams, notes, graph = sample_signals
    h1 = fuse(scams, notes, graph).audit_trail.inputs_hash
    h2 = fuse(scams, notes, graph).audit_trail.inputs_hash
    assert h1 == h2
