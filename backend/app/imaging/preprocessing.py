"""Adaptive preprocessing - multiple pipelines selected based on image profile."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def preprocess_adaptive(image: np.ndarray, profile: dict[str, Any]) -> dict[str, Any]:
    """
    Select and apply preprocessing based on image profile.

    Returns dict with:
    - processed: the preprocessed image (grayscale)
    - threshold: binary threshold version
    - pipeline_used: name of the pipeline applied
    - confidence: how confident we are in this pipeline choice
    """
    design_type = profile.get("likely_design_type", "general")
    is_photograph = profile.get("is_photograph", False)
    is_high_contrast = profile.get("is_high_contrast", False)
    brightness = profile.get("brightness", 128)

    # Ensure grayscale
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.astype(np.uint8)

    candidates: list[dict[str, Any]] = []

    # Pipeline 1: Clean drawing (high contrast, low background noise)
    if not is_photograph or is_high_contrast:
        result = _pipeline_clean_drawing(gray)
        candidates.append(result)

    # Pipeline 2: Photograph (more robust to noise and shadows)
    if is_photograph:
        result = _pipeline_photograph(gray)
        candidates.append(result)

    # Pipeline 3: High-density pattern (many small features)
    if profile.get("is_high_density", False):
        result = _pipeline_high_density(gray)
        candidates.append(result)

    # Pipeline 4: Low-contrast image (enhance first)
    if brightness > 200 or brightness < 50:
        result = _pipeline_extreme_brightness(gray)
        candidates.append(result)

    # Pipeline 5: Complex/artistic image
    if profile.get("is_complex", False):
        result = _pipeline_complex(gray)
        candidates.append(result)

    # Always include default pipeline as fallback
    result_default = _pipeline_default(gray)
    candidates.append(result_default)

    # Select best candidate based on feature detection quality
    best = _select_best_candidate(candidates, gray)
    return best


def _pipeline_clean_drawing(gray: np.ndarray) -> dict[str, Any]:
    """Pipeline for scanned or clean drawings."""
    # Minimal preprocessing, emphasize edges
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, threshold = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return {
        "processed": blurred,
        "threshold": threshold,
        "pipeline_used": "clean_drawing",
        "confidence": 0.95,
    }


def _pipeline_photograph(gray: np.ndarray) -> dict[str, Any]:
    """Pipeline for photographs and real-world images."""
    # More robust preprocessing for noise and shadows
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    blurred = cv2.medianBlur(blurred, 5)

    # CLAHE for local contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(10, 10))
    enhanced = clahe.apply(blurred)

    # Adaptive thresholding for varying lighting
    threshold = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    return {
        "processed": enhanced,
        "threshold": threshold,
        "pipeline_used": "photograph",
        "confidence": 0.88,
    }


def _pipeline_high_density(gray: np.ndarray) -> dict[str, Any]:
    """Pipeline for images with many small features."""
    # Preserve fine details
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Bilateral filter to preserve edges while reducing noise
    bilateral = cv2.bilateralFilter(blurred, 9, 75, 75)

    _, threshold = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel, iterations=1)

    return {
        "processed": bilateral,
        "threshold": threshold,
        "pipeline_used": "high_density",
        "confidence": 0.82,
    }


def _pipeline_extreme_brightness(gray: np.ndarray) -> dict[str, Any]:
    """Pipeline for very bright or very dark images."""
    # Normalize histogram
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
    _, threshold = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return {
        "processed": enhanced,
        "threshold": threshold,
        "pipeline_used": "extreme_brightness",
        "confidence": 0.80,
    }


def _pipeline_complex(gray: np.ndarray) -> dict[str, Any]:
    """Pipeline for complex artistic or detailed images."""
    # More aggressive noise reduction
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    bilateral = cv2.bilateralFilter(blurred, 11, 100, 100)

    # Multi-scale threshold
    _, threshold = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Morphological cleanup to remove small noise
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel, iterations=1)
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel, iterations=1)

    return {
        "processed": bilateral,
        "threshold": threshold,
        "pipeline_used": "complex",
        "confidence": 0.75,
    }


def _pipeline_default(gray: np.ndarray) -> dict[str, Any]:
    """Default fallback pipeline."""
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    blurred = cv2.medianBlur(blurred, 3)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(blurred)

    _, threshold = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel)

    return {
        "processed": enhanced,
        "threshold": threshold,
        "pipeline_used": "default",
        "confidence": 0.70,
    }


def _select_best_candidate(
    candidates: list[dict[str, Any]], gray: np.ndarray
) -> dict[str, Any]:
    """
    Select best preprocessing result based on feature detection quality.

    Scores based on:
    - Number of contours detected (not too many, not too few)
    - Edge continuity
    - Connected component characteristics
    """
    best_candidate = candidates[0]
    best_score = -1.0

    target_contour_range = (20, 300)  # Look for this many contours
    target_component_range = (5, 200)

    for candidate in candidates:
        threshold = candidate["threshold"]

        # Count contours
        contours, _ = cv2.findContours(threshold, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contour_count = len(contours)

        # Count components
        num_labels, _ = cv2.connectedComponents(threshold)

        # Score based on proximity to target ranges
        contour_score = 1.0 - abs(contour_count - (target_contour_range[0] + target_contour_range[1]) / 2.0) / max(target_contour_range)
        contour_score = max(0.0, min(1.0, contour_score))

        component_score = 1.0 - abs(num_labels - (target_component_range[0] + target_component_range[1]) / 2.0) / max(target_component_range)
        component_score = max(0.0, min(1.0, component_score))

        # Combined score
        combined_score = (contour_score * 0.5 + component_score * 0.3) * candidate.get("confidence", 0.7)

        if combined_score > best_score:
            best_score = combined_score
            best_candidate = candidate

    return best_candidate
