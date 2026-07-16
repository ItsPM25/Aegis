"""Plate-family linkage tests — defect-signature matching must be exact and honest."""

from aegis_command.intel import plate_families


def _note(eid, denom, defects, district, lat, lon, ts, verdict="fake"):
    return {
        "event_id": eid,
        "denomination": denom,
        "verdict": verdict,
        "missing_features": defects,
        "timestamp": ts,
        "location_hint": {"district": district, "lat": lat, "lon": lon},
    }


def test_identical_signature_is_high_tier():
    fams = plate_families([
        _note("n1", "500", ["security_thread", "microprint"], "Jamtara", 23.96, 86.80, "2026-07-07T10:00:00Z"),
        _note("n2", "500", ["security_thread", "microprint"], "Dhanbad", 23.79, 86.43, "2026-07-09T10:00:00Z"),
    ])
    assert len(fams) == 1
    assert fams[0]["tier"] == "high"
    assert fams[0]["shared_defects"] == ["microprint", "security_thread"]
    assert fams[0]["districts"] == ["Dhanbad", "Jamtara"]
    assert fams[0]["span_km"] > 30  # genuinely spans districts


def test_one_shared_defect_is_possible_tier():
    fams = plate_families([
        _note("n1", "500", ["security_thread", "microprint"], "Jamtara", 23.96, 86.80, "2026-07-07T10:00:00Z"),
        _note("n2", "500", ["security_thread", "latent_image"], "Dhanbad", 23.79, 86.43, "2026-07-09T10:00:00Z"),
    ])
    assert len(fams) == 1
    assert fams[0]["tier"] == "possible"
    assert fams[0]["shared_defects"] == ["security_thread"]


def test_no_shared_defects_no_family():
    fams = plate_families([
        _note("n1", "500", ["security_thread"], "Jamtara", 23.96, 86.80, "2026-07-07T10:00:00Z"),
        _note("n2", "500", ["color_shifting_ink"], "Deoghar", 24.48, 86.69, "2026-07-11T10:00:00Z"),
    ])
    assert fams == []


def test_different_denominations_never_link():
    """A ₹500 plate cannot print a ₹2000 note — denominations are separate."""
    fams = plate_families([
        _note("n1", "500", ["security_thread"], "Jamtara", 23.96, 86.80, "2026-07-07T10:00:00Z"),
        _note("n2", "2000", ["security_thread"], "Dhanbad", 23.79, 86.43, "2026-07-09T10:00:00Z"),
    ])
    assert fams == []


def test_genuine_notes_excluded():
    fams = plate_families([
        _note("n1", "500", ["security_thread"], "Jamtara", 23.96, 86.80, "2026-07-07T10:00:00Z"),
        _note("n2", "500", ["security_thread"], "Dhanbad", 23.79, 86.43, "2026-07-09T10:00:00Z", verdict="genuine"),
    ])
    assert fams == []


def test_events_ordered_by_time_and_links_reported():
    fams = plate_families([
        _note("n2", "500", ["security_thread", "microprint"], "Dhanbad", 23.79, 86.43, "2026-07-09T10:00:00Z"),
        _note("n1", "500", ["security_thread", "microprint"], "Jamtara", 23.96, 86.80, "2026-07-07T10:00:00Z"),
    ])
    ev = fams[0]["events"]
    assert [e["event_id"] for e in ev] == ["n1", "n2"]  # chronological
    assert fams[0]["links"][0]["tier"] == "high"


# ── campaign fingerprinting ──────────────────────────────────────────────────

from aegis_command.intel import scam_campaigns

SCRIPT_A = (
    "This is Inspector Sharma from CBI. An FIR has been registered against your "
    "Aadhaar for money laundering. Stay on this video call and do not disconnect."
)
SCRIPT_A_VARIANT = (
    "This is Inspector Sharma from Alwar cyber cell. A money laundering case is "
    "registered against your Aadhaar. Transfer Rs 49,999 as a refundable deposit."
)
SCRIPT_B = "Congratulations! You won the mega lottery jackpot. Claim your prize now."


def _scam(eid, text, district, ts, phone=None, verdict="scam"):
    return {
        "event_id": eid, "raw_text": text, "verdict": verdict,
        "scam_type": "digital_arrest", "phone_number": phone,
        "timestamp": ts, "location_hint": {"district": district},
    }


def test_identical_script_high_tier():
    camps = scam_campaigns([
        _scam("s1", SCRIPT_A, "Jamtara", "2026-07-07T10:00:00Z"),
        _scam("s2", SCRIPT_A, "Deoghar", "2026-07-08T10:00:00Z"),
    ])
    assert len(camps) == 1
    assert camps[0]["tier"] == "high"
    assert camps[0]["district_spread"] == ["Jamtara", "Deoghar"]  # chronological


def test_script_variant_links_as_campaign():
    """Localized edits of one template still cluster (the real seed data)."""
    camps = scam_campaigns([
        _scam("s1", SCRIPT_A, "Jamtara", "2026-07-07T10:00:00Z"),
        _scam("s2", SCRIPT_A_VARIANT, "Alwar", "2026-07-08T10:00:00Z"),
    ])
    assert len(camps) == 1
    assert camps[0]["tier"] in ("possible", "probable")
    assert camps[0]["links"][0]["similarity"] > 0.3


def test_unrelated_scripts_do_not_link():
    camps = scam_campaigns([
        _scam("s1", SCRIPT_A, "Jamtara", "2026-07-07T10:00:00Z"),
        _scam("s2", SCRIPT_B, "Alwar", "2026-07-08T10:00:00Z"),
    ])
    assert camps == []


def test_shared_phone_links_even_with_different_scripts():
    """Same callback device = same operator, whatever the script says."""
    camps = scam_campaigns([
        _scam("s1", SCRIPT_A, "Jamtara", "2026-07-07T10:00:00Z", phone="+91-99999"),
        _scam("s2", SCRIPT_B, "Alwar", "2026-07-08T10:00:00Z", phone="+91-99999"),
    ])
    assert len(camps) == 1
    assert camps[0]["tier"] == "high"
    assert "phone" in camps[0]["links"][0]["basis"]


def test_legit_messages_excluded():
    camps = scam_campaigns([
        _scam("s1", SCRIPT_A, "Jamtara", "2026-07-07T10:00:00Z"),
        _scam("s2", SCRIPT_A, "Deoghar", "2026-07-08T10:00:00Z", verdict="legit"),
    ])
    assert camps == []
