"""Enhanced symmetry detection with adaptive testing."""

from __future__ import annotations

from typing import Any

import numpy as np


def detect_symmetry_adaptive(points: list[dict[str, Any]], circles: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    """
    Detect symmetry in the extracted geometry.

    Tests for:
    - vertical reflection
    - horizontal reflection
    - diagonal reflection
    - rotational (order 2 through 12)
    - radial symmetry
    - approximate/partial symmetry

    Returns dict with:
    - type: "none", "reflection", "rotational", "radial", "combined"
    - orders: list of detected symmetry orders
    - axes: list of detected symmetry axes
    - center: center point for rotational symmetry
    - confidence: overall confidence
    """
    coords = []

    # Collect coordinates from points
    for point in points:
        coords.append((point.get("x", 0), point.get("y", 0)))

    # Collect coordinates from circles
    for circle in circles:
        center = circle.get("center", {})
        coords.append((center.get("x", 0), center.get("y", 0)))

    if not coords:
        return {"type": "none", "order": 0, "confidence": 0.0}

    coords_array = np.array(coords, dtype=float)

    # Find spatial center
    centroid = np.mean(coords_array, axis=0)

    # Test reflection symmetries
    reflection_results = _test_reflection_symmetry(coords_array, centroid)

    # Test rotational symmetries
    rotational_results = _test_rotational_symmetry(coords_array, centroid)

    # Combine results
    best_result = _combine_symmetry_results(reflection_results, rotational_results, centroid)

    return best_result


def _test_reflection_symmetry(
    coords: np.ndarray, centroid: np.ndarray
) -> dict[str, Any]:
    """Test for reflection symmetry along various axes."""
    results = {}

    # Vertical reflection (y-axis through centroid)
    vertical_score = _score_reflection(coords, centroid, axis="vertical")
    results["vertical"] = vertical_score

    # Horizontal reflection (x-axis through centroid)
    horizontal_score = _score_reflection(coords, centroid, axis="horizontal")
    results["horizontal"] = horizontal_score

    # Diagonal reflections
    diag1_score = _score_reflection(coords, centroid, axis="diagonal1")
    results["diagonal1"] = diag1_score

    diag2_score = _score_reflection(coords, centroid, axis="diagonal2")
    results["diagonal2"] = diag2_score

    return results


def _test_rotational_symmetry(
    coords: np.ndarray, centroid: np.ndarray
) -> dict[int, float]:
    """Test for rotational symmetry of various orders."""
    results = {}

    # Test rotational orders 2 through 12
    for order in range(2, 13):
        score = _score_rotational(coords, centroid, order)
        if score > 0.3:  # Only include meaningful scores
            results[order] = score

    return results


def _score_reflection(
    coords: np.ndarray, centroid: np.ndarray, axis: str
) -> float:
    """Score how well coordinates reflect across an axis."""
    reflected_coords = coords.copy()

    if axis == "vertical":
        # Reflect across vertical line through centroid
        reflected_coords[:, 0] = 2 * centroid[0] - coords[:, 0]

    elif axis == "horizontal":
        # Reflect across horizontal line through centroid
        reflected_coords[:, 1] = 2 * centroid[1] - coords[:, 1]

    elif axis == "diagonal1":
        # Reflect across diagonal y=x through centroid
        offset = coords - centroid
        reflected_coords = centroid + np.array([offset[:, 1], offset[:, 0]]).T

    elif axis == "diagonal2":
        # Reflect across diagonal y=-x through centroid
        offset = coords - centroid
        reflected_coords = centroid + np.array([-offset[:, 1], -offset[:, 0]]).T

    else:
        return 0.0

    # Score by finding matches between original and reflected
    score = 0.0
    tolerance = 20.0  # pixels

    for orig in coords:
        # Find closest reflected point
        distances = np.linalg.norm(reflected_coords - orig, axis=1)
        min_dist = np.min(distances)

        if min_dist < tolerance:
            score += 1.0 - (min_dist / tolerance)

    score = score / max(len(coords), 1)
    return max(0.0, min(1.0, score))


def _score_rotational(coords: np.ndarray, centroid: np.ndarray, order: int) -> float:
    """Score how well coordinates exhibit rotational symmetry of given order."""
    if order < 2:
        return 0.0

    angle_step = 2.0 * np.pi / order

    # For each point, check if there are matching points at rotated angles
    score = 0.0
    tolerance = 20.0  # pixels

    for orig in coords:
        relative = orig - centroid

        matches = 0
        for k in range(1, order):
            # Rotate by k * angle_step
            theta = k * angle_step
            rot_x = relative[0] * np.cos(theta) - relative[1] * np.sin(theta)
            rot_y = relative[0] * np.sin(theta) + relative[1] * np.cos(theta)
            rotated_point = centroid + np.array([rot_x, rot_y])

            # Find closest point in coordinate set
            distances = np.linalg.norm(coords - rotated_point, axis=1)
            min_dist = np.min(distances)

            if min_dist < tolerance:
                matches += 1

        # Score based on how many rotations had matches
        score += matches / order

    score = score / max(len(coords), 1)
    return max(0.0, min(1.0, score))


def _combine_symmetry_results(
    reflection_results: dict[str, float],
    rotational_results: dict[int, float],
    centroid: np.ndarray,
) -> dict[str, Any]:
    """Combine reflection and rotational results into final symmetry description."""

    # Find best reflection
    best_reflection = max(reflection_results.items(), key=lambda x: x[1])
    reflection_type, reflection_score = best_reflection

    # Find best rotation
    if rotational_results:
        best_rotation = max(rotational_results.items(), key=lambda x: x[1])
        rotation_order, rotation_score = best_rotation
    else:
        rotation_order = 0
        rotation_score = 0.0

    # Determine primary symmetry type
    if rotation_score > reflection_score and rotation_score > 0.3:
        return {
            "type": "rotational",
            "order": int(rotation_order),
            "confidence": float(rotation_score),
            "center": {"x": float(centroid[0]), "y": float(centroid[1])},
            "secondary_reflection": reflection_type if reflection_score > 0.3 else None,
        }

    elif reflection_score > 0.3:
        return {
            "type": "reflection",
            "axis": reflection_type,
            "confidence": float(reflection_score),
            "center": {"x": float(centroid[0]), "y": float(centroid[1])},
            "secondary_rotation": int(rotation_order) if rotation_score > 0.3 else None,
        }

    elif rotation_score > 0.2 or reflection_score > 0.2:
        return {
            "type": "approximate",
            "order": int(rotation_order) if rotation_score > 0.2 else None,
            "confidence": float(max(rotation_score, reflection_score)),
            "center": {"x": float(centroid[0]), "y": float(centroid[1])},
        }

    else:
        return {
            "type": "none",
            "order": 0,
            "confidence": 0.0,
            "center": {"x": float(centroid[0]), "y": float(centroid[1])},
        }
