"""Synthetic corpus: deterministic, both classes, no leaked duplicates."""

from aegis_fraud_shield.config import CorpusConfig
from aegis_fraud_shield.corpus import generate_corpus


def test_corpus_is_deterministic():
    a = generate_corpus(CorpusConfig(seed=42))
    b = generate_corpus(CorpusConfig(seed=42))
    assert a.equals(b)


def test_corpus_has_both_classes_and_families():
    df = generate_corpus()
    assert set(df["label"].unique()) == {0, 1}
    origins = set(df["origin"])
    assert "synth_digital_arrest" in origins
    assert any(o.startswith("synth_legit") for o in origins)


def test_corpus_has_no_duplicate_texts():
    df = generate_corpus()
    assert df["text"].is_unique
