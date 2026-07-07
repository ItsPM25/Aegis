"""OpenCV security-feature checks — the feature-level detection layer.

This is what lifts the module beyond "whole-note fake/real": each check
inspects the region where a real security feature lives and reports
pass/fail **with a numeric score**, so the UI and the fusion LLM can say
*which* feature is missing (contract field `missing_features`) and the
result stays auditable.

Checks implemented (the three the synthetic ground truth covers):
- **security_thread** — column-darkness scan around the known thread x-band;
  a genuine windowed thread shows a narrow, strongly darker column.
- **watermark** — brightness lift of the watermark oval vs its surround.
- **microprint** — Laplacian variance (sharpness) of the microprint band;
  counterfeits reproduce it blurred or not at all.

Denomination is inferred from the note's dominant hue (₹2000 magenta vs
₹500 stone grey) — cheap, and enough for the demo's two denominations.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .config import NOTE_SIZE
from .synth import MICROPRINT_Y, SECURITY_THREAD, THREAD_X, WATERMARK, WATERMARK_X
from .synth import MICROPRINT as MICROPRINT_FEATURE


@dataclass
class FeatureCheck:
    """Outcome of one security-feature inspection."""

    feature: str
    passed: bool
    score: float  # the measured statistic (interpretation depends on check)
    threshold: float
    detail: str


def _to_canonical(img_bgr: np.ndarray) -> np.ndarray:
    """Resize to the canonical working size so region fractions line up."""
    return cv2.resize(img_bgr, NOTE_SIZE, interpolation=cv2.INTER_AREA)


def check_security_thread(img_bgr: np.ndarray) -> FeatureCheck:
    """Genuine thread = narrow column much darker than its neighbourhood."""
    img = _to_canonical(img_bgr)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape
    x0, x1 = int(w * (THREAD_X - 0.08)), int(w * (THREAD_X + 0.08))
    band = gray[int(h * 0.08): int(h * 0.92), x0:x1]
    col_means = band.mean(axis=0)
    # Contrast of the darkest column against the band's own median.
    contrast = float(np.median(col_means) - col_means.min())
    threshold = 12.0
    return FeatureCheck(
        feature=SECURITY_THREAD,
        passed=contrast >= threshold,
        score=round(contrast, 2),
        threshold=threshold,
        detail=f"thread-band darkness contrast {contrast:.1f} (needs >= {threshold})",
    )


def check_watermark(img_bgr: np.ndarray) -> FeatureCheck:
    """Genuine watermark = local brightness lift in the watermark oval."""
    img = _to_canonical(img_bgr)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape
    cx, cy = int(w * WATERMARK_X), int(h * 0.45)
    inner = gray[cy - 40: cy + 40, cx - 30: cx + 30]
    outer = gray[cy - 60: cy + 60, cx - 55: cx + 55]
    # True annulus: subtract the inner block so the surround isn't diluted.
    ring_mean = (outer.sum() - inner.sum()) / (outer.size - inner.size)
    lift = float(inner.mean() - ring_mean)
    threshold = 4.0
    return FeatureCheck(
        feature=WATERMARK,
        passed=lift >= threshold,
        score=round(lift, 2),
        threshold=threshold,
        detail=f"watermark brightness lift {lift:.1f} (needs >= {threshold})",
    )


def check_microprint(img_bgr: np.ndarray) -> FeatureCheck:
    """Genuine microprint = sharp band => high Laplacian variance."""
    img = _to_canonical(img_bgr)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    y = int(h * MICROPRINT_Y)
    band = gray[max(y - 4, 0): min(y + 20, h), int(w * 0.06): int(w * 0.60)]
    # 3x3 denoise first so sensor noise can't masquerade as sharp print.
    band = cv2.GaussianBlur(band, (3, 3), 0)
    sharpness = float(cv2.Laplacian(band, cv2.CV_64F).var())
    threshold = 60.0
    return FeatureCheck(
        feature=MICROPRINT_FEATURE,
        passed=sharpness >= threshold,
        score=round(sharpness, 2),
        threshold=threshold,
        detail=f"microprint sharpness {sharpness:.1f} (needs >= {threshold})",
    )


def run_all_checks(img_bgr: np.ndarray) -> list[FeatureCheck]:
    return [
        check_security_thread(img_bgr),
        check_watermark(img_bgr),
        check_microprint(img_bgr),
    ]


def missing_features(img_bgr: np.ndarray) -> list[str]:
    """Contract-ready list of failed security features."""
    return [c.feature for c in run_all_checks(img_bgr) if not c.passed]


def infer_denomination(img_bgr: np.ndarray) -> str:
    """₹2000 is magenta, ₹500 stone grey — separable on saturation + hue."""
    img = _to_canonical(img_bgr)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hue = float(np.median(hsv[:, :, 0]))
    sat = float(np.median(hsv[:, :, 1]))
    if sat < 30:
        return "500"  # near-grey
    # OpenCV hue is 0-179; magenta/pink sits around 140-175.
    if 120 <= hue <= 179 and sat >= 30:
        return "2000"
    return "unknown"
