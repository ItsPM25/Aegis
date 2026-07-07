"""Marker rules: the contract sample must trip its markers; legit text must not."""

from aegis_fraud_shield.markers import (
    ALL_MARKERS,
    AUTHORITY_IMPERSONATION,
    CRYPTO_OR_GIFTCARD_DEMAND,
    FAKE_FIR_OR_CASE,
    PERSONAL_DATA_REQUEST,
    SUSPICIOUS_LINK,
    URGENCY_PRESSURE,
    VIDEO_CALL_ISOLATION,
    detect_markers,
    infer_scam_type,
    marker_names,
)

DIGITAL_ARREST = (
    "This is Inspector Sharma from CBI. An FIR has been registered against your Aadhaar "
    "for money laundering. Stay on this video call and do not disconnect. Transfer the "
    "verification amount in USDT immediately or a warrant will be issued."
)


def test_digital_arrest_script_trips_core_markers():
    found = set(marker_names(DIGITAL_ARREST))
    assert {
        AUTHORITY_IMPERSONATION,
        FAKE_FIR_OR_CASE,
        URGENCY_PRESSURE,
        CRYPTO_OR_GIFTCARD_DEMAND,
        VIDEO_CALL_ISOLATION,
    } <= found


def test_markers_only_use_contract_enum_names():
    for hit in detect_markers(DIGITAL_ARREST):
        assert hit.marker in ALL_MARKERS
        assert hit.evidence, "every hit must carry evidence spans"


def test_personal_chat_is_clean():
    assert marker_names("Hey, are we still meeting for lunch tomorrow at 1pm?") == []


def test_genuine_otp_warning_does_not_trip_data_request():
    text = "482913 is your OTP for HDFC net banking login. Do not share this OTP with anyone."
    assert PERSONAL_DATA_REQUEST not in marker_names(text)


def test_shortened_link_detected():
    assert SUSPICIOUS_LINK in marker_names("Update KYC at https://bit.ly/kyc-upd8 now")


def test_scam_type_digital_arrest_wins():
    assert infer_scam_type(DIGITAL_ARREST, marker_names(DIGITAL_ARREST)) == "digital_arrest"


def test_scam_type_lottery():
    text = "Congratulations! You won Rs 25,00,000 in the lucky draw. Claim your prize now."
    assert infer_scam_type(text, marker_names(text)) == "lottery"
