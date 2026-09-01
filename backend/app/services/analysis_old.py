from __future__ import annotations

from typing import Any

import cv2
import networkx as nx
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
    height, width = image.shape[:2]
    scale = min(1.0, target_max_dim / max(height, width))
    if scale < 1.0:
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
    return image


def _find_artwork_region(image: np.ndarray) -> tuple[np.ndarray, tuple[int, int, int, int], dict[str, Any] | None]:
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
                best = {"x": x, "y": y, "w": w, "h": h, "contour": approx}
                break

    height, width = gray.shape[:2]
    if best is None:
        return image, (0, 0, width, height), None

    x, y, w, h = best["x"], best["y"], best["w"], best["h"]
    padded = image[max(0, y - 8): min(height, y + h + 8), max(0, x - 8): min(width, x + w + 8)]
    return padded, (max(0, x - 8), max(0, y - 8), min(width, x + w + 8) - max(0, x - 8), min(height, y + h + 8) - max(0, y - 8)), best


def _preprocess_image(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[int, int, int, int]]:
    normalized = _normalize_image(image)
    cropped, bbox, _ = _find_artwork_region(normalized)

    if cropped.ndim == 3:
        gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    else:
        gray = cropped.astype(np.uint8)

    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    gray = cv2.medianBlur(gray, 3)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    _, threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(threshold) > 127:
        threshold = cv2.bitwise_not(threshold)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel)
    return cropped, gray, threshold, bbox


def _filter_circle_candidates(gray: np.ndarray, circles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not circles:
        return []

    candidate_list: list[dict[str, Any]] = []
    for idx, circle in enumerate(circles):
        x = int(circle["center"]["x"])
        y = int(circle["center"]["y"])
        radius = float(circle["radius"])
        if radius < 8 or radius > min(gray.shape[:2]) * 0.45:
            continue
        margin = max(10, int(radius * 0.15))
        if x < margin or y < margin or x > gray.shape[1] - margin or y > gray.shape[0] - margin:
            continue

        mask = np.zeros_like(gray)
        cv2.circle(mask, (x, y), int(radius), 255, thickness=-1)
        support = float(np.mean(gray[mask > 0])) if np.any(mask > 0) else 0.0
        if support < 15 or support > 245:
            continue
        candidate_list.append({
            "id": f"circle_{idx}",
            "type": "circle",
            "center": {"x": float(x), "y": float(y)},
            "radius": radius,
            "confidence": max(0.4, min(0.9, (1.0 - abs(128 - support) / 128.0) * 0.75 + 0.25)),
        })

    candidate_list.sort(key=lambda item: item["radius"], reverse=True)
    kept: list[dict[str, Any]] = []
    for candidate in candidate_list:
        center = candidate["center"]
        if any(np.hypot(center["x"] - item["center"]["x"], center["y"] - item["center"]["y"]) < max(10.0, item["radius"] * 0.35) for item in kept):
            continue
        kept.append(candidate)
    return kept[:12]


def _extract_points_and_lines(threshold: np.ndarray) -> dict[str, list[dict[str, Any]]]:
    contours, _ = cv2.findContours(threshold, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    points: list[dict[str, Any]] = []
    lines: list[dict[str, Any]] = []

    for index, contour in enumerate(sorted(contours, key=cv2.contourArea, reverse=True)[:30]):
        area = cv2.contourArea(contour)
        if area < 18:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if w < 4 or h < 4:
            continue

        m = cv2.moments(contour)
        if m["m00"] > 0:
            cx = float(m["m10"] / m["m00"])
            cy = float(m["m01"] / m["m00"])
            points.append({"id": f"point_{index}", "x": cx, "y": cy, "confidence": 0.82})

        if area > 140:
            epsilon = 0.015 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            if len(approx) >= 2:
                pts = approx.reshape(-1, 2)
                start = pts[0]
                end = pts[-1]
                if np.linalg.norm(start - end) > 6:
                    lines.append({
                        "id": f"line_{index}",
                        "type": "line",
                        "points": [{"x": float(x), "y": float(y)} for x, y in [pts[0], pts[-1]]],
                        "confidence": 0.74,
                    })
                if len(pts) >= 8:
                    lines.append({
                        "id": f"polyline_{index}",
                        "type": "polyline",
                        "points": [{"x": float(x), "y": float(y)} for x, y in pts[:20]],
                        "confidence": 0.68,
                    })

    deduped_points: list[dict[str, Any]] = []
    seen_points: set[tuple[float, float]] = set()
    for point in points:
        key = (round(point["x"], 2), round(point["y"], 2))
        if key in seen_points:
            continue
        deduped_points.append(point)
        seen_points.add(key)
    return {"points": deduped_points, "lines": lines[:18]}


def _extract_circles(gray: np.ndarray) -> list[dict[str, Any]]:
    circles: list[dict[str, Any]] = []
    detected = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.4,
        minDist=max(25, gray.shape[0] // 12),
        param1=120,
        param2=32,
        minRadius=12,
        maxRadius=min(gray.shape[:2]) // 3,
    )
    if detected is not None:
        for idx, circle in enumerate(detected[0]):
            x, y, radius = circle
            circles.append({
                "id": f"circle_{idx}",
                "type": "circle",
                "center": {"x": float(x), "y": float(y)},
                "radius": float(radius),
                "confidence": 0.8,
            })
    return _filter_circle_candidates(gray, circles)


def _extract_curves(threshold: np.ndarray) -> list[dict[str, Any]]:
    contours, _ = cv2.findContours(threshold, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    curves: list[dict[str, Any]] = []
    for index, contour in enumerate(sorted(contours, key=cv2.contourArea, reverse=True)[:12]):
        area = cv2.contourArea(contour)
        if area < 200:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if w < 12 or h < 12:
            continue
        epsilon = 0.008 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        if len(approx) >= 10:
            pts = approx.reshape(-1, 2)
            curves.append({
                "id": f"curve_{index}",
                "type": "bezier",
                "points": [{"x": float(x), "y": float(y)} for x, y in pts[:30]],
                "confidence": 0.71,
            })
    return curves[:8]


def _build_topology_enhanced(
    points: list[dict[str, Any]], lines: list[dict[str, Any]], circles: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build topology graph with better structure awareness."""
    graph = nx.Graph()

    # Add point nodes
    for point in points:
        graph.add_node(
            f"point_{point.get('id', '')}",
            kind="point",
            x=point.get("x", 0),
            y=point.get("y", 0),
        )

    # Add circle nodes
    for circle in circles:
        center = circle.get("center", {})
        graph.add_node(
            f"circle_{circle.get('id', '')}",
            kind="circle",
            x=center.get("x", 0),
            y=center.get("y", 0),
            radius=circle.get("radius", 0),
        )

    # Add line edges
    for line in lines:
        points_on_line = line.get("points", [])
        if len(points_on_line) >= 2:
            for i in range(len(points_on_line) - 1):
                p1 = points_on_line[i]
                p2 = points_on_line[i + 1]
                graph.add_edge(
                    f"line_segment_{id(line)}_{i}",
                    f"line_segment_{id(line)}_{i+1}",
                )

    # Calculate metrics
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
        "components": components,
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

    construction_steps = _get_construction_steps(design_type, geometry, symmetry)

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
        "motifs": [{"id": m["id"], "count": 1} for m in motifs[:4]],
        "repetition": [],
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


def _get_construction_steps(
    design_type: str, geometry: dict[str, Any], symmetry: dict[str, Any]
) -> list[str]:
    """Get construction steps appropriate for the design type."""
    steps = ["Analyze image profile", "Preprocess adaptively", "Extract geometric primitives"]

    if design_type == "dense_pattern":
        steps.extend([
            "Identify repeated motifs",
            "Detect pattern grid or tiling",
            "Extract motif structure",
            "Apply repetition rules",
        ])
    elif design_type == "photographed_ornament":
        steps.extend([
            "Isolate artwork region",
            "Enhance contrast",
            "Extract major curves and shapes",
            "Identify symmetries",
        ])
    elif design_type == "clean_geometric":
        steps.extend([
            "Extract primitives with high confidence",
            "Build connectivity graph",
            "Detect symmetry axes",
        ])
    else:
        steps.extend([
            "Build component relationships",
            "Detect local symmetries",
        ])

    if symmetry.get("type") != "none":
        steps.append(f"Apply {symmetry.get('type', 'unknown')} symmetry")

    steps.extend(["Validate topology", "Generate reconstruction", "Finalize parameters"])

    return steps


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

    # Geometric confidence: do we have enough features?
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


# Keep legacy functions for backward compatibility

    coords: list[tuple[float, float]] = []
    for point in points:
        coords.append((point["x"], point["y"]))
    for circle in circles:
        center = circle["center"]
        coords.append((center["x"], center["y"]))

    if not coords:
        return {"type": "none", "order": 0, "confidence": 0.0}

    array = np.array(coords, dtype=float)
    centroid = np.mean(array, axis=0)
    rel = array - centroid
    if len(rel) < 2:
        return {"type": "none", "order": 0, "confidence": 0.0}

    best = {"type": "none", "order": 0, "confidence": 0.0}
    for order in [2, 3, 4, 6, 8]:
        target = 2 * np.pi / order
        score = 0.0
        for vector in rel:
            angle = np.arctan2(vector[1], vector[0])
            nearest = round(angle / target) * target
            score += 1.0 - min(abs(angle - nearest), abs(angle - (nearest + 2 * np.pi)), abs(angle - (nearest - 2 * np.pi))) / (np.pi / order)
        confidence = max(0.0, min(1.0, score / max(len(rel), 1)))
        if confidence > best["confidence"]:
            best = {"type": "rotational", "order": order, "confidence": float(confidence)}

    if best["confidence"] < 0.2:
        return {"type": "none", "order": 0, "confidence": float(best["confidence"])}
    return best


def _detect_repetition(points: list[dict[str, Any]], circles: list[dict[str, Any]]) -> dict[str, Any]:
    coords = [(p["x"], p["y"]) for p in points]
    coords.extend([(c["center"]["x"], c["center"]["y"]) for c in circles])
    if len(coords) < 3:
        return {"patterns": []}

    arr = np.array(coords, dtype=float)
    pairwise = np.linalg.norm(arr[:, None, :] - arr[None, :, :], axis=2)
    upper = pairwise[np.triu_indices(len(arr), 1)]
    upper = upper[upper > 0]
    spacing = float(np.median(upper)) if upper.size else 0.0
    if spacing <= 0:
        return {"patterns": []}

    repeated: list[dict[str, Any]] = []
    for center in arr:
        nearby = np.linalg.norm(arr - center, axis=1)
        count = int(np.sum(nearby <= spacing * 1.6))
        if count >= 3:
            repeated.append({"center": [float(center[0]), float(center[1])], "count": count, "spacing": spacing, "confidence": 0.62})
            break

    return {"patterns": repeated}


def _build_topology(points: list[dict[str, Any]], lines: list[dict[str, Any]], circles: list[dict[str, Any]]) -> dict[str, Any]:
    graph = nx.Graph()
    for point in points:
        graph.add_node(f"point_{point['id']}", kind="point", x=point["x"], y=point["y"])
    for circle in circles:
        graph.add_node(f"circle_{circle['id']}", kind="circle", x=circle["center"]["x"], y=circle["center"]["y"], radius=circle["radius"])
    for line in lines:
        if not line.get("points"):
            continue
        start = line["points"][0]
        end = line["points"][-1]
        a = f"segment_{len(graph.nodes)}_a"
        b = f"segment_{len(graph.nodes)}_b"
        graph.add_node(a, kind="segment", x=start["x"], y=start["y"])
        graph.add_node(b, kind="segment", x=end["x"], y=end["y"])
        graph.add_edge(a, b)

    nodes = [{"id": node_id, "kind": data.get("kind"), "x": data.get("x"), "y": data.get("y"), "radius": data.get("radius")} for node_id, data in graph.nodes(data=True)]
    edges = [{"source": u, "target": v} for u, v in graph.edges()]
    return {"nodes": nodes, "edges": edges, "components": nx.number_connected_components(graph), "cycles": list(nx.simple_cycles(graph))}


def _build_geometry_dict(image: np.ndarray, threshold: np.ndarray, gray: np.ndarray) -> dict[str, Any]:
    point_data = _extract_points_and_lines(threshold)
    raw_circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.4,
        minDist=max(25, gray.shape[0] // 12),
        param1=120,
        param2=32,
        minRadius=12,
        maxRadius=min(gray.shape[:2]) // 3,
    )
    raw_circle_list: list[dict[str, Any]] = []
    if raw_circles is not None:
        for idx, circle in enumerate(raw_circles[0]):
            x, y, radius = circle
            raw_circle_list.append({
                "id": f"raw_circle_{idx}",
                "type": "circle",
                "center": {"x": float(x), "y": float(y)},
                "radius": float(radius),
                "confidence": 0.8,
            })

    circles = _extract_circles(gray)
    curves = _extract_curves(threshold)
    lines = point_data["lines"]
    points = point_data["points"]

    seen: set[tuple[float, float]] = set()
    enriched_points: list[dict[str, Any]] = []
    for point in points:
        key = (round(point["x"], 2), round(point["y"], 2))
        if key not in seen:
            enriched_points.append(point)
            seen.add(key)

    for idx, circle in enumerate(circles):
        center = circle["center"]
        key = (round(center["x"], 2), round(center["y"], 2))
        if key not in seen:
            enriched_points.append({
                "id": f"circle_anchor_{idx}",
                "x": center["x"],
                "y": center["y"],
                "confidence": circle.get("confidence", 0.75),
            })
            seen.add(key)

    for idx, line in enumerate(lines):
        for point in line.get("points", []):
            key = (round(point["x"], 2), round(point["y"], 2))
            if key in seen:
                continue
            enriched_points.append({
                "id": f"line_anchor_{idx}",
                "x": point["x"],
                "y": point["y"],
                "confidence": line.get("confidence", 0.6),
            })
            seen.add(key)

    points = enriched_points
    if not points and not circles and not curves:
        raise GeometryError("The image does not contain enough clear geometric structure for reconstruction.")

    symmetry = _detect_symmetry(points, circles)
    repetition = _detect_repetition(points, circles)
    topology = _build_topology(points, lines, circles)

    motif_entries: list[dict[str, Any]] = []
    if circles:
        motif_entries.append({"id": "motif_01", "type": "repeated_circle_framework", "confidence": 0.72, "count": len(circles)})
    if curves:
        motif_entries.append({"id": "motif_02", "type": "major_curves", "confidence": 0.68, "count": len(curves)})

    derived_geometry = {
        "points": points[:40],
        "lines": lines[:8],
        "polylines": [line for line in lines if line.get("type") == "polyline"][:4],
        "circles": circles[:8],
        "ellipses": [],
        "arcs": [],
        "bezier_curves": curves[:6],
        "polygons": [],
        "intersections": [],
    }

    geometry = {
        "raw_detection": {
            "contours": len(point_data["lines"]) + len(curves),
            "circle_candidates": raw_circle_list[:50],
        },
        "geometry": derived_geometry,
        "motifs": motif_entries,
        "symmetry": symmetry,
        "repetition": repetition,
        "topology": topology,
        "measurements": {
            "radius_values": [circle["radius"] for circle in circles],
            "point_count": len(points),
            "circle_count": len(circles),
            "curve_count": len(curves),
        },
        "metrics": {
            "primitive_count": len(points[:40]) + len(circles[:8]) + len(curves[:6]) + len(lines[:8]),
            "curve_count": len(curves[:6]),
            "intersection_count": len(topology["cycles"]),
            "loop_count": len(topology["cycles"]),
        },
        "constraints": {
            "symmetry": symmetry,
            "repetition": repetition,
            "dominant_radius": float(np.median([circle["radius"] for circle in circles])) if circles else None,
        },
        "grammar": {},
        "debug": {
            "source_width": int(image.shape[1]),
            "source_height": int(image.shape[0]),
            "filtered_circle_count": len(circles),
            "curve_count": len(curves),
            "points_count": len(points),
        },
    }
    return geometry


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
        isolated, region_bbox, region_confidence = _find_artwork_region(normalized)
        if region_confidence and region_confidence.get("confidence", 0) > 0.5:
            if isolated.ndim == 3:
                isolated_gray = cv2.cvtColor(isolated, cv2.COLOR_BGR2GRAY)
            else:
                isolated_gray = isolated.astype(np.uint8)
            processed_gray = isolated_gray
    else:
        isolated = normalized
        region_bbox = (0, 0, normalized.shape[1], normalized.shape[0])

    # Stage 5: Adaptive geometry extraction
    geometry = extract_geometry_adaptive(isolated, threshold, processed_gray, profile)

    # Stage 6: Motif discovery
    motifs = discover_motifs(geometry)
    repetitions = find_repeated_motifs(motifs)

    # Stage 7: Symmetry and repetition detection
    all_points = geometry.get("points", [])
    all_circles = geometry.get("circles", [])
    symmetry = detect_symmetry_adaptive(all_points, all_circles, profile)

    # Stage 8: Topology analysis (using NetworkX)
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
            "confidence": preprocessing_result.get("confidence", 0.7),
        },
        "geometry": {
            "points": geometry.get("points", [])[:40],
            "lines": geometry.get("lines", [])[:8],
            "polylines": geometry.get("polylines", [])[:4],
            "circles": geometry.get("circles", [])[:8],
            "ellipses": geometry.get("ellipses", [])[:4],
            "arcs": geometry.get("arcs", [])[:4],
            "bezier_curves": geometry.get("curves", [])[:6],
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
            "aspect_ratio": profile.get("aspect_ratio", 0),
            "point_count": len(all_points),
            "circle_count": len(all_circles),
            "line_count": len(geometry.get("lines", [])),
            "curve_count": len(geometry.get("curves", [])),
            "motif_count": len(motifs),
            "repetition_patterns": len(repetitions),
        },
        "metadata": {
            "design_type": profile.get("likely_design_type", "general"),
            "edge_density": profile.get("edge_density", 0),
            "complexity": profile.get("is_complex", False),
        },
    }

    return result

