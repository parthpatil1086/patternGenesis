"""Image profile analysis - characterize input images adaptively."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def analyze_image_profile(image: np.ndarray) -> dict[str, Any]:
    """
    Analyze image characteristics to guide adaptive processing.

    Returns profile containing:
    - dimensions and aspect ratio
    - brightness and contrast
    - color characteristics
    - edge and feature density
    - likely background type
    - complexity metrics
    """
    if image is None or image.size == 0:
        return {}

    height, width = image.shape[:2]
    aspect_ratio = float(width) / float(height) if height > 0 else 1.0

    # Color analysis
    is_color = len(image.shape) == 3 and image.shape[2] == 3
    if is_color:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Brightness and contrast
    brightness = float(np.mean(gray))
    std_dev = float(np.std(gray))
    contrast_ratio = std_dev / (brightness + 1e-6)
    is_high_contrast = std_dev > 50

    # Edge density (Canny edge detection)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    edge_density = float(np.sum(edges > 0)) / (width * height) if (width * height) > 0 else 0.0

    # Connected components (potential design elements)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    num_labels, _ = cv2.connectedComponents(binary)
    component_density = float(num_labels) / (width * height + 1e-6)

    # Dominant colors (if color image)
    dominant_hue = None
    color_uniformity = 0.0
    if is_color:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hue_channel = hsv[:, :, 0]
        dominant_hue = float(np.median(hue_channel))
        color_uniformity = 1.0 - (float(np.std(hue_channel)) / 180.0)  # Normalize to 0-1

    # Likely image type
    is_photograph = is_high_contrast and edge_density > 0.05
    is_clean_drawing = not is_high_contrast or (edge_density < 0.15 and component_density < 0.1)
    is_high_density = component_density > 0.2
    is_complex = edge_density > 0.3

    # Background analysis
    border_pixels = np.concatenate([
        gray[0, :],          # top row
        gray[-1, :],         # bottom row
        gray[:, 0],          # left column
        gray[:, -1],         # right column
    ])
    border_brightness = float(np.mean(border_pixels))
    background_type = "light" if border_brightness > 150 else "dark" if border_brightness < 100 else "medium"

    # Likely foreground (assuming foreground has different brightness than border)
    foreground_brightness = 255 - border_brightness if border_brightness > 127 else border_brightness

    profile = {
        "width": int(width),
        "height": int(height),
        "aspect_ratio": aspect_ratio,
        "is_color": bool(is_color),
        "brightness": brightness,
        "contrast_ratio": contrast_ratio,
        "is_high_contrast": bool(is_high_contrast),
        "edge_density": edge_density,
        "component_density": component_density,
        "dominant_hue": dominant_hue,
        "color_uniformity": color_uniformity,
        "is_photograph": bool(is_photograph),
        "is_clean_drawing": bool(is_clean_drawing),
        "is_high_density": bool(is_high_density),
        "is_complex": bool(is_complex),
        "background_type": background_type,
        "border_brightness": border_brightness,
        "foreground_brightness": foreground_brightness,
        "likely_design_type": _classify_design_type(
            is_photograph, is_clean_drawing, is_high_density, is_complex, edge_density, component_density
        ),
    }

    return profile


def _classify_design_type(
    is_photograph: bool,
    is_clean_drawing: bool,
    is_high_density: bool,
    is_complex: bool,
    edge_density: float,
    component_density: float,
) -> str:
    """Classify the likely design type based on characteristics."""
    if is_photograph and is_complex:
        return "photographed_ornament"
    if is_clean_drawing and not is_high_density:
        return "clean_geometric"
    if is_high_density and edge_density > 0.2:
        return "dense_pattern"
    if component_density > 0.3:
        return "repeated_motif"
    if not is_photograph and edge_density < 0.1:
        return "minimal_geometric"
    return "general"
