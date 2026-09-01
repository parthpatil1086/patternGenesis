"""Motif discovery and similarity analysis."""

from __future__ import annotations

from typing import Any

import numpy as np


def discover_motifs(geometry: dict[str, Any], min_motif_size: int = 2) -> list[dict[str, Any]]:
    """
    Discover repeated geometric motifs in the extracted geometry.

    A motif is a group of primitives that form a meaningful local structure.

    Returns list of motif descriptions with:
    - id: unique motif identifier
    - components: list of primitive IDs
    - bounding_box: spatial extent
    - center: centroid
    - size: rough size measure
    - complexity: estimated complexity
    - confidence: how confident we are it's a motif
    """
    motifs = []

    # Group nearby primitives into candidate motifs
    candidates = _group_nearby_primitives(geometry)

    # Analyze each candidate group
    for idx, candidate_group in enumerate(candidates):
        motif = {
            "id": f"motif_{idx:02d}",
            "components": candidate_group["primitives"],
            "bounding_box": candidate_group["bbox"],
            "center": candidate_group["center"],
            "size": candidate_group["size"],
            "complexity": candidate_group["complexity"],
            "confidence": candidate_group["confidence"],
            "primitive_types": candidate_group["types"],
        }
        motifs.append(motif)

    return motifs


def find_repeated_motifs(motifs: list[dict[str, Any]], similarity_threshold: float = 0.7) -> list[dict[str, Any]]:
    """
    Identify motifs that repeat or are similar to each other.

    Returns list of repetition patterns with:
    - base_motif: the motif that repeats
    - instances: list of motif IDs that match
    - transformation: type of transformation (translation, rotation, reflection, etc.)
    - count: how many instances found
    - confidence: how confident we are
    """
    if not motifs:
        return []

    repetitions = []

    # Compare each pair of motifs
    for i in range(len(motifs)):
        for j in range(i + 1, len(motifs)):
            similarity, transformation = _compare_motifs(motifs[i], motifs[j])

            if similarity > similarity_threshold:
                # Check if this pattern already exists in repetitions
                existing = False
                for rep in repetitions:
                    if motifs[i]["id"] in rep["instances"] or motifs[j]["id"] in rep["instances"]:
                        # Extend existing pattern
                        if motifs[j]["id"] not in rep["instances"]:
                            rep["instances"].append(motifs[j]["id"])
                        existing = True
                        break

                if not existing:
                    repetitions.append({
                        "base_motif": motifs[i]["id"],
                        "instances": [motifs[i]["id"], motifs[j]["id"]],
                        "transformation": transformation,
                        "count": 2,
                        "similarity": float(similarity),
                        "confidence": float(similarity),
                    })

    return repetitions


def _group_nearby_primitives(geometry: dict[str, Any], proximity_factor: float = 1.5) -> list[dict[str, Any]]:
    """
    Group primitives that are near each other into candidate motifs.

    Uses spatial clustering to find naturally grouped primitives.
    """
    candidates = []

    # Collect all primitives with positions
    primitives_with_pos = []

    for point in geometry.get("points", []):
        primitives_with_pos.append({
            "id": point.get("id", ""),
            "type": "point",
            "x": point.get("x", 0),
            "y": point.get("y", 0),
            "confidence": point.get("confidence", 0.5),
        })

    for circle in geometry.get("circles", []):
        primitives_with_pos.append({
            "id": circle.get("id", ""),
            "type": "circle",
            "x": circle.get("center", {}).get("x", 0),
            "y": circle.get("center", {}).get("y", 0),
            "confidence": circle.get("confidence", 0.5),
        })

    for curve in geometry.get("curves", []):
        points = curve.get("points", [])
        if points:
            x = np.mean([p.get("x", 0) for p in points])
            y = np.mean([p.get("y", 0) for p in points])
            primitives_with_pos.append({
                "id": curve.get("id", ""),
                "type": "curve",
                "x": x,
                "y": y,
                "confidence": curve.get("confidence", 0.5),
            })

    # Simple clustering: group by proximity
    positions = np.array([[p["x"], p["y"]] for p in primitives_with_pos])

    if len(positions) == 0:
        return candidates

    # Use a simple greedy clustering
    used = set()
    for i, center_pos in enumerate(positions):
        if i in used:
            continue

        # Find all points near this one
        distances = np.linalg.norm(positions - center_pos, axis=1)
        median_dist = np.median(distances[distances > 0]) if np.any(distances > 0) else 50.0
        threshold = median_dist * proximity_factor

        nearby_indices = np.where(distances <= threshold)[0]

        if len(nearby_indices) > 0:
            group_ids = [primitives_with_pos[idx]["id"] for idx in nearby_indices]
            group_types = set([primitives_with_pos[idx]["type"] for idx in nearby_indices])

            # Calculate group properties
            group_positions = positions[nearby_indices]
            bbox_min = group_positions.min(axis=0)
            bbox_max = group_positions.max(axis=0)
            bbox = {
                "x": float(bbox_min[0]),
                "y": float(bbox_min[1]),
                "width": float(bbox_max[0] - bbox_min[0]),
                "height": float(bbox_max[1] - bbox_min[1]),
            }
            center = {
                "x": float(np.mean(group_positions[:, 0])),
                "y": float(np.mean(group_positions[:, 1])),
            }
            size = float(max(bbox["width"], bbox["height"]))
            complexity = len(nearby_indices) / 10.0  # Rough measure

            candidates.append({
                "primitives": group_ids,
                "bbox": bbox,
                "center": center,
                "size": size,
                "complexity": min(1.0, complexity),
                "confidence": 0.6 + (len(nearby_indices) / 20.0),
                "types": list(group_types),
            })

            for idx in nearby_indices:
                used.add(idx)

    return candidates


def _compare_motifs(motif1: dict[str, Any], motif2: dict[str, Any]) -> tuple[float, str]:
    """
    Compare two motifs for similarity.

    Returns (similarity_score, transformation_type).

    Transformation types:
    - translation
    - rotation
    - reflection
    - scaling
    - combined
    """
    c1 = np.array([motif1["center"]["x"], motif1["center"]["y"]])
    c2 = np.array([motif2["center"]["x"], motif2["center"]["y"]])

    s1 = motif1.get("size", 1.0)
    s2 = motif2.get("size", 1.0)

    # Size ratio (detect scaling)
    size_ratio = min(s1, s2) / max(s1, s2 + 1e-6)

    # Distance between centers (detect translation)
    center_dist = np.linalg.norm(c2 - c1)

    # Complexity comparison
    comp1 = motif1.get("complexity", 0.5)
    comp2 = motif2.get("complexity", 0.5)
    comp_similarity = 1.0 - abs(comp1 - comp2)

    # Type similarity
    types1 = set(motif1.get("primitive_types", []))
    types2 = set(motif2.get("primitive_types", []))
    type_intersection = len(types1 & types2)
    type_union = len(types1 | types2)
    type_similarity = type_intersection / (type_union + 1e-6)

    # Combined similarity (more similar = higher score)
    similarity = (
        (size_ratio * 0.3)  # Prefer same-sized motifs
        + (comp_similarity * 0.3)  # Prefer same complexity
        + (type_similarity * 0.4)  # Prefer same types
    )

    # Determine transformation type
    if abs(size_ratio - 1.0) > 0.2:
        transformation = "scaling"
    elif center_dist > max(s1, s2):
        transformation = "translation"
    else:
        transformation = "proximity"

    return float(similarity), transformation
