"""Advanced geometry extraction with validation and deduplication."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def extract_geometry_adaptive(
    image: np.ndarray, threshold: np.ndarray, gray: np.ndarray, profile: dict[str, Any]
) -> dict[str, Any]:
    """
    Extract geometric primitives with adaptive detection based on image profile.

    Returns dict with:
    - points: detected point features
    - lines: detected line segments
    - polylines: detected polyline chains
    - circles: detected circles
    - ellipses: detected ellipses
    - arcs: detected arcs
    - curves: detected curves/Bezier paths
    - intersections: detected intersections
    - raw_contours: for reference
    """
    geometry = {
        "points": [],
        "lines": [],
        "polylines": [],
        "circles": [],
        "ellipses": [],
        "arcs": [],
        "curves": [],
        "paths": [],
        "intersections": [],
        "raw_contours": [],
    }

    # Adaptive parameters based on profile
    edge_density = profile.get("edge_density", 0.1)
    component_density = profile.get("component_density", 0.05)
    design_type = profile.get("likely_design_type", "general")

    # Extract from threshold
    # Thresholds are often white foreground on a light scan. Normalize the mask
    # here so contour tracing follows the artwork rather than the page border.
    foreground = threshold
    if float(np.mean(threshold[[0, -1], :])) > 127 or float(np.mean(threshold[:, [0, -1]])) > 127:
        foreground = cv2.bitwise_not(threshold)

    contours, hierarchy = cv2.findContours(foreground, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    geometry["raw_contours"] = len(contours)

    geometry["paths"] = _extract_contour_paths(contours, hierarchy, gray.shape)

    # Sort by area for processing
    sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)

    # Adaptive limits based on image complexity
    max_contours_to_process = int(100 if design_type == "dense_pattern" else 50)
    max_contours_to_process = min(max_contours_to_process, len(sorted_contours))

    # Extract different primitive types
    for idx, contour in enumerate(sorted_contours[:max_contours_to_process]):
        area = cv2.contourArea(contour)
        if area < 5:  # Skip very small contours
            continue

        bbox = cv2.boundingRect(contour)
        x, y, w, h = bbox

        if w < 2 or h < 2:  # Skip very small bounding boxes
            continue

        # Try to classify and extract the primitive
        primitive_type = _classify_contour(contour, area)

        if primitive_type == "circle":
            circle_data = _fit_circle(contour, area)
            if circle_data and circle_data["confidence"] > 0.4:
                geometry["circles"].append({**circle_data, "contour_idx": idx})

        elif primitive_type == "ellipse":
            ellipse_data = _fit_ellipse(contour, area)
            if ellipse_data and ellipse_data["confidence"] > 0.4:
                geometry["ellipses"].append({**ellipse_data, "contour_idx": idx})

        elif primitive_type == "line":
            line_data = _fit_line(contour)
            if line_data and line_data["confidence"] > 0.3:
                geometry["lines"].append({**line_data, "contour_idx": idx})

        elif primitive_type == "arc":
            arc_data = _fit_arc(contour)
            if arc_data and arc_data["confidence"] > 0.3:
                geometry["arcs"].append({**arc_data, "contour_idx": idx})

        else:  # curve/polyline
            curve_data = _fit_curve(contour)
            if curve_data and curve_data["confidence"] > 0.3:
                if len(curve_data.get("points", [])) > 3:
                    geometry["curves"].append({**curve_data, "contour_idx": idx})
                else:
                    geometry["polylines"].append({**curve_data, "contour_idx": idx})

        # Extract key points (corners, centroids)
        points = _extract_keypoints(contour)
        for point in points:
            geometry["points"].append(point)

    # Post-processing: deduplicate and merge similar primitives
    geometry = _deduplicate_geometry(geometry, gray)
    geometry = _detect_intersections(geometry)

    return geometry


def _extract_contour_paths(
    contours: list[np.ndarray], hierarchy: np.ndarray | None, shape: tuple[int, int]
) -> list[dict[str, Any]]:
    """Keep meaningful traced contours as the faithful reconstruction layer."""
    height, width = shape[:2]
    image_area = float(height * width)
    diagonal = float(np.hypot(width, height))
    candidates: list[dict[str, Any]] = []

    for index, contour in enumerate(contours):
        perimeter = float(cv2.arcLength(contour, True))
        area = abs(float(cv2.contourArea(contour)))
        if perimeter < max(20.0, diagonal * 0.04) or area < image_area * 0.00001:
            continue
        x, y, box_width, box_height = cv2.boundingRect(contour)
        if x <= 1 and y <= 1 and box_width >= width - 2 and box_height >= height - 2:
            continue

        epsilon = max(0.5, min(perimeter * 0.012, diagonal * 0.018))
        simplified = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
        if len(simplified) < 3:
            continue
        moments = cv2.moments(contour)
        centroid = {
            "x": float(moments["m10"] / moments["m00"]) if moments["m00"] else float(x + box_width / 2),
            "y": float(moments["m01"] / moments["m00"]) if moments["m00"] else float(y + box_height / 2),
        }
        parent = int(hierarchy[0][index][3]) if hierarchy is not None else -1
        candidates.append({
            "id": f"path_{index}",
            "type": "path",
            "points": [{"x": float(px), "y": float(py)} for px, py in simplified[:200]],
            "closed": True,
            "area": area,
            "perimeter": perimeter,
            "bbox": {"x": x, "y": y, "width": box_width, "height": box_height},
            "centroid": centroid,
            "parent": f"path_{parent}" if parent >= 0 else None,
            "confidence": float(min(1.0, 0.45 + min(0.4, perimeter / (diagonal * 8.0)) + min(0.15, area / image_area))),
        })

    # Keep the structural contour budget broad, while excluding tiny specks.
    return sorted(candidates, key=lambda item: (item["perimeter"], item["area"]), reverse=True)[:120]


def _classify_contour(contour: np.ndarray, area: float) -> str:
    """Classify what type of primitive a contour likely represents."""
    if len(contour) < 5:
        return "line"

    # Fit ellipse to classify
    if len(contour) >= 5:
        try:
            ellipse = cv2.fitEllipse(contour)
            axes = sorted([ellipse[1][0], ellipse[1][1]])
            ratio = axes[1] / (axes[0] + 1e-6)

            # The axes are sorted, so circularity is closeness to 1, not a lower bound.
            if ratio <= 1.35:
                return "circle"
            elif ratio <= 2.5:
                return "ellipse"
        except Exception:
            pass

    # Check if it's line-like
    hull = cv2.convexHull(contour)
    if len(hull) <= 4:
        return "line"

    # Check if it's arc-like
    arc_score = _score_arc_likelihood(contour)
    if arc_score > 0.7:
        return "arc"

    return "curve"


def _fit_circle(contour: np.ndarray, area: float) -> dict[str, Any] | None:
    """Fit a circle to a contour and return circle parameters."""
    if len(contour) < 5:
        return None

    try:
        center, radius = cv2.minEnclosingCircle(contour)
        if radius < 2:
            return None

        # Score how well the contour fits the circle
        circle_area = np.pi * radius * radius
        fit_score = min(area, circle_area) / max(area, circle_area + 1e-6)

        return {
            "id": f"circle_{id(contour)}",
            "type": "circle",
            "center": {"x": float(center[0]), "y": float(center[1])},
            "radius": float(radius),
            "area": float(area),
            "confidence": float(fit_score * 0.9),
        }
    except Exception:
        return None


def _fit_ellipse(contour: np.ndarray, area: float) -> dict[str, Any] | None:
    """Fit an ellipse to a contour."""
    if len(contour) < 5:
        return None

    try:
        ellipse = cv2.fitEllipse(contour)
        center, axes, angle = ellipse

        if axes[0] < 2 or axes[1] < 2:
            return None

        # Score fit quality
        ellipse_area = np.pi * axes[0] * axes[1] / 4
        fit_score = min(area, ellipse_area) / max(area, ellipse_area + 1e-6)

        return {
            "id": f"ellipse_{id(contour)}",
            "type": "ellipse",
            "center": {"x": float(center[0]), "y": float(center[1])},
            "axes": {"a": float(axes[0]), "b": float(axes[1])},
            "angle": float(angle),
            "area": float(area),
            "confidence": float(fit_score * 0.85),
        }
    except Exception:
        return None


def _fit_line(contour: np.ndarray) -> dict[str, Any] | None:
    """Fit a line to a contour."""
    try:
        points = contour.reshape(-1, 2).astype(np.float32)
        if len(points) < 2:
            return None

        vx, vy, x0, y0 = cv2.fitLine(points, cv2.DIST_L2, 0, 0.01, 0.01)

        # Get endpoints
        p1 = np.array([x0 - vx * 1000, y0 - vy * 1000], dtype=np.int32)
        p2 = np.array([x0 + vx * 1000, y0 + vy * 1000], dtype=np.int32)

        return {
            "id": f"line_{id(contour)}",
            "type": "line",
            "points": [
                {"x": float(p1[0]), "y": float(p1[1])},
                {"x": float(p2[0]), "y": float(p2[1])},
            ],
            "confidence": 0.75,
        }
    except Exception:
        return None


def _fit_arc(contour: np.ndarray) -> dict[str, Any] | None:
    """Detect if contour is arc-like and return arc parameters."""
    if len(contour) < 5:
        return None

    try:
        center, radius = cv2.minEnclosingCircle(contour)
        points = contour.reshape(-1, 2).astype(np.float32)

        # Calculate angles of points relative to center
        angles = []
        for p in points:
            angle = np.arctan2(p[1] - center[1], p[0] - center[0])
            angles.append(angle)

        if not angles:
            return None

        angle_span = max(angles) - min(angles)

        # If angle span is less than 180 degrees, it's an arc
        if angle_span < np.pi:
            return {
                "id": f"arc_{id(contour)}",
                "type": "arc",
                "center": {"x": float(center[0]), "y": float(center[1])},
                "radius": float(radius),
                "angle_start": float(min(angles)),
                "angle_end": float(max(angles)),
                "confidence": 0.70,
            }
    except Exception:
        pass

    return None


def _fit_curve(contour: np.ndarray) -> dict[str, Any] | None:
    """Fit a curve/Bezier approximation to a contour."""
    try:
        # Simplify contour
        epsilon = 0.005 * cv2.arcLength(contour, False)
        approx = cv2.approxPolyDP(contour, epsilon, False)

        if len(approx) < 2:
            return None

        points = []
        for point in approx.reshape(-1, 2)[:50]:  # Limit to 50 points
            points.append({"x": float(point[0]), "y": float(point[1])})

        return {
            "id": f"curve_{id(contour)}",
            "type": "curve",
            "points": points,
            "length": float(cv2.arcLength(contour, False)),
            "confidence": 0.72,
        }
    except Exception:
        return None


def _extract_keypoints(contour: np.ndarray) -> list[dict[str, Any]]:
    """Extract important points from a contour (corners, centroid)."""
    points = []

    try:
        # Centroid
        M = cv2.moments(contour)
        if M["m00"] > 0:
            cx = float(M["m10"] / M["m00"])
            cy = float(M["m01"] / M["m00"])
            points.append({
                "id": f"centroid_{id(contour)}",
                "x": cx,
                "y": cy,
                "type": "centroid",
                "confidence": 0.85,
            })

        # Corners (using corner detection)
        corners = cv2.goodFeaturesToTrack(
            cv2.cvtColor(contour.astype(np.uint8), cv2.COLOR_GRAY2BGR)[:, :, 0:1],
            maxCorners=4,
            qualityLevel=0.01,
            minDistance=10,
            useHarrisDetector=False,
        )

        if corners is not None:
            for corner in corners[:4]:
                x, y = corner.ravel()
                points.append({
                    "id": f"corner_{id(contour)}_{len(points)}",
                    "x": float(x),
                    "y": float(y),
                    "type": "corner",
                    "confidence": 0.70,
                })
    except Exception:
        pass

    return points


def _score_arc_likelihood(contour: np.ndarray) -> float:
    """Score how arc-like a contour is."""
    if len(contour) < 5:
        return 0.0

    try:
        center, radius = cv2.minEnclosingCircle(contour)
        points = contour.reshape(-1, 2).astype(np.float32)

        # Calculate distances from center
        distances = np.linalg.norm(points - center, axis=1)

        # If most points are roughly the same distance from center, it's arc-like
        std_dist = np.std(distances)
        mean_dist = np.mean(distances)

        return 1.0 - (std_dist / (mean_dist + 1e-6))
    except Exception:
        return 0.0


def _deduplicate_geometry(geometry: dict[str, Any], gray: np.ndarray) -> dict[str, Any]:
    """Remove duplicate and overlapping primitives."""
    # Deduplicate circles
    if geometry["circles"]:
        dedup_circles = []
        seen_centers = set()
        for circle in sorted(geometry["circles"], key=lambda c: c["confidence"], reverse=True):
            center = (round(circle["center"]["x"], 1), round(circle["center"]["y"], 1))
            if center not in seen_centers:
                dedup_circles.append(circle)
                seen_centers.add(center)
        geometry["circles"] = dedup_circles

    # Deduplicate points
    if geometry["points"]:
        dedup_points = []
        seen_pts = set()
        for point in sorted(geometry["points"], key=lambda p: p.get("confidence", 0), reverse=True):
            key = (round(point["x"], 1), round(point["y"], 1))
            if key not in seen_pts:
                dedup_points.append(point)
                seen_pts.add(key)
        geometry["points"] = dedup_points[:40]  # Limit points

    return geometry


def _detect_intersections(geometry: dict[str, Any]) -> dict[str, Any]:
    """Detect intersections between lines and curves."""
    intersections = []

    # This is a simplified version - full implementation would detect actual intersections
    # between line segments, curves, etc.

    geometry["intersections"] = intersections
    return geometry
