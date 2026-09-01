"""
Image analysis service using the adaptive generalized pipeline.

This module orchestrates the complete pipeline for analyzing design images:
1. Image profiling
2. Adaptive preprocessing
3. Geometry extraction
4. Motif discovery
5. Symmetry and repetition detection
6. Topology analysis
7. Grammar generation
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np
from fastapi import UploadFile

from app.core.exceptions import DotDetectionError, GeometryError, InvalidImageError
from app.grammar.schema import build_grammar
from app.imaging.profile import analyze_image_profile
from app.imaging.preprocessing import preprocess_adaptive
from app.geometry.extraction import extract_geometry_adaptive
from app.analysis.motifs import discover_motifs, find_repeated_motifs
from app.analysis.symmetry import detect_symmetry_adaptive


VALID_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}


def _decode_image(file: UploadFile) -> np.ndarray:
    """Decode and validate uploaded image."""
    if not file or not getattr(file, "filename", None):
        raise InvalidImageError("No image file was provided.")
    content_type = getattr(file, "content_type", None)
    filename = getattr(file, "filename", "")
    if content_type and content_type not in VALID_IMAGE_TYPES:
        raise InvalidImageError("Unsupported image format.")
    if filename and not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        raise InvalidImageError("Unsupported image format.")

    contents = file.file.read()
    if not contents:
        raise InvalidImageError("Uploaded image is empty.")

    array = np.frombuffer(contents, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise InvalidImageError("Uploaded file is not a valid image.")
    return image


def _normalize_image(image: np.ndarray, target_max_dim: int = 1200) -> np.ndarray:
    """Normalize image size for processing."""
    height, width = image.shape[:2]
    scale = min(1.0, target_max_dim / max(height, width))
    if scale < 1.0:
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
    return image


def _find_artwork_region(image: np.ndarray) -> tuple[np.ndarray, tuple[int, int, int, int], dict[str, Any] | None]:
    """
    Attempt to isolate the artwork region from the background.

    Useful for photographs or images with frames/borders.

    Returns:
    - cropped: the cropped image
    - bbox: bounding box coordinates
    - region_info: metadata about the detected region
    """
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.astype(np.uint8)

    blurred = cv2.GaussianBlur(gray, (9, 9), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    best: dict[str, Any] | None = None

    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        area = cv2.contourArea(contour)
        if area < 0.15 * gray.size:
            continue
        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            continue
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(contour)
            if w * h > 0.2 * gray.size:
                best = {"x": x, "y": y, "w": w, "h": h, "contour": approx, "confidence": 0.75}
                break

    height, width = gray.shape[:2]
    if best is None:
        return image, (0, 0, width, height), None

    x, y, w, h = best["x"], best["y"], best["w"], best["h"]
    padded = image[max(0, y - 8): min(height, y + h + 8), max(0, x - 8): min(width, x + w + 8)]
    bbox = (max(0, x - 8), max(0, y - 8), min(width, x + w + 8) - max(0, x - 8), min(height, y + h + 8) - max(0, y - 8))
    return padded, bbox, best


def _build_topology_enhanced(
    points: list[dict[str, Any]], lines: list[dict[str, Any]], circles: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build topology graph with spatial structure analysis."""
    import networkx as nx

    graph = nx.Graph()

    # Add point nodes
    for point in points:
        graph.add_node(
            f"point_{point.get('id', 'unknown')}",
            kind="point",
            x=point.get("x", 0),
            y=point.get("y", 0),
        )

    # Add circle nodes
    for circle in circles:
        center = circle.get("center", {})
        graph.add_node(
            f"circle_{circle.get('id', 'unknown')}",
            kind="circle",
            x=center.get("x", 0),
            y=center.get("y", 0),
            radius=circle.get("radius", 0),
        )

    # Add line edges
    for line_idx, line in enumerate(lines):
        points_on_line = line.get("points", [])
        if len(points_on_line) >= 2:
            for i in range(len(points_on_line) - 1):
                graph.add_edge(
                    f"line_{line_idx}_p{i}",
                    f"line_{line_idx}_p{i+1}",
                )

    nodes = [
        {
            "id": node_id,
            "kind": data.get("kind"),
            "x": data.get("x"),
            "y": data.get("y"),
            "radius": data.get("radius"),
        }
        for node_id, data in graph.nodes(data=True)
    ]
    edges = [{"source": u, "target": v} for u, v in graph.edges()]
    components = nx.number_connected_components(graph)

    return {
        "nodes": nodes,
        "edges": edges,
        "components": int(components),
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def _generate_adaptive_grammar(
    geometry: dict[str, Any],
    symmetry: dict[str, Any],
    motifs: list[dict[str, Any]],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Generate parametric grammar based on detected structure."""
    design_type = profile.get("likely_design_type", "general")

    construction_steps = [
        "Analyze image profile",
        "Preprocess adaptively",
        "Extract geometric primitives",
    ]

    if design_type == "dense_pattern":
        construction_steps.extend([
            "Identify repeated motifs",
            "Detect pattern grid or tiling",
            "Extract motif structure",
            "Apply repetition rules",
        ])
    elif design_type == "photographed_ornament":
        construction_steps.extend([
            "Isolate artwork region",
            "Enhance contrast",
            "Extract major curves and shapes",
            "Identify symmetries",
        ])
    elif design_type == "clean_geometric":
        construction_steps.extend([
            "Extract primitives with high confidence",
            "Build connectivity graph",
            "Detect symmetry axes",
        ])
    else:
        construction_steps.extend([
            "Build component relationships",
            "Detect local symmetries",
        ])

    if symmetry.get("type") != "none":
        construction_steps.append(f"Apply {symmetry.get('type', 'unknown')} symmetry")

    construction_steps.extend(["Validate topology", "Generate reconstruction", "Finalize parameters"])

    grammar = {
        "grammar_version": "2.0",
        "design_type": design_type,
        "primitives": [
            {"type": "point", "count": len(geometry.get("points", []))},
            {"type": "line", "count": len(geometry.get("lines", []))},
            {"type": "circle", "count": len(geometry.get("circles", []))},
            {"type": "curve", "count": len(geometry.get("bezier_curves", []))},
        ],
        "symmetry": symmetry,
        "motifs": [{"id": m["id"], "type": "discovered", "count": 1} for m in motifs[:4]],
        "topology": {
            "connected_components": 1,
            "hierarchy_depth": 2,
        },
        "construction_steps": construction_steps,
        "parameters": {
            "scale": profile.get("width", 1),
            "symmetry_order": symmetry.get("order", 1),
            "motif_count": len(motifs),
        },
        "constraints": [],
        "metadata": {
            "source": "adaptive-general-engine",
            "version": "2.0",
        },
    }

    return grammar


def _calculate_confidence_scores(
    geometry: dict[str, Any],
    symmetry: dict[str, Any],
    motifs: list[dict[str, Any]],
    profile: dict[str, Any],
) -> dict[str, float]:
    """Calculate confidence scores for different aspects of analysis."""
    point_count = len(geometry.get("points", []))
    circle_count = len(geometry.get("circles", []))
    curve_count = len(geometry.get("curves", []))

    # Geometric confidence
    geometry_confidence = 0.5
    if point_count > 5:
        geometry_confidence += 0.2
    if circle_count > 0:
        geometry_confidence += 0.15
    if curve_count > 0:
        geometry_confidence += 0.15
    geometry_confidence = min(1.0, geometry_confidence)

    # Symmetry confidence
    symmetry_confidence = float(symmetry.get("confidence", 0.0))

    # Motif confidence
    motif_confidence = 0.5
    if len(motifs) > 1:
        motif_confidence = 0.7

    # Overall confidence
    overall_confidence = (
        geometry_confidence * 0.4 + symmetry_confidence * 0.3 + motif_confidence * 0.3
    )

    return {
        "geometry": float(geometry_confidence),
        "symmetry": float(symmetry_confidence),
        "motifs": float(motif_confidence),
        "overall": float(overall_confidence),
    }


async def analyze_image(file: UploadFile) -> dict[str, Any]:
    """
    Analyze an uploaded image using the adaptive generalized pipeline.

    Pipeline stages:
    1. Decode and validate image
    2. Profile image characteristics
    3. Adaptive preprocessing based on profile
    4. Design region isolation (optional)
    5. Adaptive geometry extraction
    6. Motif discovery
    7. Symmetry and repetition detection
    8. Topology analysis
    9. Grammar generation
    10. Confidence scoring and reporting
    """
    # Stage 1: Decode image
    image = _decode_image(file)

    # Stage 2: Profile image
    profile = analyze_image_profile(image)

    # Normalize for processing
    normalized = _normalize_image(image)

    # Stage 3: Adaptive preprocessing
    preprocessing_result = preprocess_adaptive(normalized, profile)
    processed_gray = preprocessing_result["processed"]
    threshold = preprocessing_result["threshold"]

    # Stage 4: Design region isolation (optional, based on profile)
    if profile.get("is_photograph", False):
        isolated, region_bbox, region_info = _find_artwork_region(normalized)
        if region_info and region_info.get("confidence", 0) > 0.5:
            if isolated.ndim == 3:
                isolated_gray = cv2.cvtColor(isolated, cv2.COLOR_BGR2GRAY)
            else:
                isolated_gray = isolated.astype(np.uint8)
            processed_gray = isolated_gray
    else:
        isolated = normalized

    # Stage 5: Adaptive geometry extraction
    geometry = extract_geometry_adaptive(isolated, threshold, processed_gray, profile)

    # Validate we have geometry
    if (not geometry.get("points") and not geometry.get("circles")
        and not geometry.get("curves") and not geometry.get("paths")):
        raise GeometryError("Could not extract meaningful geometry from the image.")

    # Stage 6: Motif discovery
    motifs = discover_motifs(geometry)
    repetitions = find_repeated_motifs(motifs)

    # Stage 7: Symmetry and repetition detection
    all_points = geometry.get("points", [])
    all_circles = geometry.get("circles", [])
    symmetry = detect_symmetry_adaptive(all_points, all_circles, profile)

    # Stage 8: Topology analysis
    topology = _build_topology_enhanced(all_points, geometry.get("lines", []), all_circles)

    # Stage 9: Grammar generation
    grammar = _generate_adaptive_grammar(geometry, symmetry, motifs, profile)

    # Stage 10: Confidence scoring
    confidence_scores = _calculate_confidence_scores(geometry, symmetry, motifs, profile)

    # Assemble final result
    result = {
        "version": "2.0",
        "image_profile": profile,
        "preprocessing": {
            "pipeline_used": preprocessing_result.get("pipeline_used", "default"),
            "confidence": float(preprocessing_result.get("confidence", 0.7)),
        },
        "geometry": {
            "points": geometry.get("points", [])[:40],
            "lines": geometry.get("lines", [])[:8],
            "polylines": geometry.get("polylines", [])[:4],
            "circles": geometry.get("circles", [])[:8],
            "ellipses": geometry.get("ellipses", [])[:4],
            "arcs": geometry.get("arcs", [])[:4],
            "bezier_curves": (geometry.get("curves", []) + geometry.get("polylines", []))[:8],
            "paths": geometry.get("paths", []),
            "intersections": geometry.get("intersections", []),
        },
        "motifs": motifs[:8],
        "repetitions": repetitions[:4],
        "symmetry": symmetry,
        "topology": topology,
        "grammar": grammar,
        "confidence": confidence_scores,
        "measurements": {
            "image_width": profile.get("width", 0),
            "image_height": profile.get("height", 0),
            "aspect_ratio": float(profile.get("aspect_ratio", 0)),
            "point_count": len(all_points),
            "circle_count": len(all_circles),
            "line_count": len(geometry.get("lines", [])),
            "curve_count": len(geometry.get("curves", [])) + len(geometry.get("polylines", [])),
            "motif_count": len(motifs),
            "repetition_patterns": len(repetitions),
        },
        "metadata": {
            "design_type": profile.get("likely_design_type", "general"),
            "edge_density": float(profile.get("edge_density", 0)),
            "complexity": bool(profile.get("is_complex", False)),
        },
        "debug": {
            "raw_contour_count": int(geometry.get("raw_contours", 0)),
            "faithful_path_count": len(geometry.get("paths", [])),
            "semantic_curve_count": len(geometry.get("curves", [])),
            "selected_preprocessing": preprocessing_result.get("pipeline_used", "default"),
            "design_region": {"x": 0, "y": 0, "width": int(isolated.shape[1]), "height": int(isolated.shape[0])},
        },
    }

    return result
