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


def _order_corners(quad: np.ndarray) -> np.ndarray:
    """Order 4 points as top-left, top-right, bottom-right, bottom-left."""
    s = quad.sum(axis=1)
    d = np.diff(quad, axis=1).ravel()
    return np.array(
        [quad[np.argmin(s)], quad[np.argmin(d)], quad[np.argmax(s)], quad[np.argmax(d)]],
        dtype=np.float32,
    )


def locate_note(img_bgr: np.ndarray) -> np.ndarray:
    """Find the note in a camera frame and perspective-correct it.

    A photo of a note on a desk puts the security-feature regions nowhere near
    their canonical fractions — every check would read the wrong pixels. This
    finds the dominant quadrilateral (15–95% of the frame), warps it to
    NOTE_SIZE, and falls back to a plain resize when the image already *is*
    the note (our renders, tight crops) or no plausible note outline exists.
    """
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_quad, best_area = None, 0.0
    frame_area = float(h * w)
    for contour in contours:
        area = cv2.contourArea(contour)
        if not (0.15 * frame_area <= area <= 0.95 * frame_area):
            continue
        approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
        if len(approx) == 4 and area > best_area:
            best_quad, best_area = approx.reshape(4, 2).astype(np.float32), area

    if best_quad is None:
        return cv2.resize(img_bgr, NOTE_SIZE, interpolation=cv2.INTER_AREA)

    src = _order_corners(best_quad)
    dst_w, dst_h = NOTE_SIZE
    dst = np.array([[0, 0], [dst_w - 1, 0], [dst_w - 1, dst_h - 1], [0, dst_h - 1]],
                   dtype=np.float32)
    return cv2.warpPerspective(img_bgr, cv2.getPerspectiveTransform(src, dst), NOTE_SIZE)


def _to_canonical(img_bgr: np.ndarray) -> np.ndarray:
    """Canonical working frame: pass through if already canonical (avoids
    re-running localisation), otherwise locate + warp."""
    if img_bgr.shape[1::-1] == NOTE_SIZE:
        return img_bgr
    return locate_note(img_bgr)


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
