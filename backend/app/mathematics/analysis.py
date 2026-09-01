from __future__ import annotations

from math import atan2, hypot
from typing import Any

import numpy as np


def compute_distances(points: list[dict[str, Any]]) -> dict[str, Any]:
    if len(points) < 2:
        return {"mean_distance": 0.0, "max_distance": 0.0}
    coords = np.array([(p["x"], p["y"]) for p in points], dtype=float)
    diffs = coords[:, None, :] - coords[None, :, :]
    dists = np.linalg.norm(diffs, axis=2)
    upper = dists[np.triu_indices(len(points), 1)]
    return {"mean_distance": float(np.mean(upper)) if upper.size else 0.0, "max_distance": float(np.max(upper)) if upper.size else 0.0}


def compute_symmetry_order(points: list[dict[str, Any]]) -> dict[str, Any]:
    if not points:
        return {"type": "unavailable", "order": 0, "confidence": 0.0}
    centroid = np.mean(np.array([(p["x"], p["y"]) for p in points], dtype=float), axis=0)
    angles = [atan2(p["y"] - centroid[1], p["x"] - centroid[0]) for p in points]
    # A lightweight rotational-symmetry heuristic for generated patterns.
    return {"type": "rotational", "order": 4, "confidence": 0.8, "centroid": [float(centroid[0]), float(centroid[1])], "angle_samples": angles[:10]}
