from __future__ import annotations

from typing import Any

from fastapi import UploadFile

from app.core.exceptions import DotDetectionError
from app.services.analysis import analyze_image


def _to_svg_path(points: list[dict[str, float]], closed: bool = False) -> str:
    if not points:
        return ""
    first = points[0]
    commands = [f"M {first['x']} {first['y']}"]
    for point in points[1:]:
        commands.append(f"L {point['x']} {point['y']}")
    return " ".join(commands) + (" Z" if closed else "")


def _normalize_paths(paths: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, float]]:
    points = [point for path in paths for point in path.get("points", [])]
    if not points:
        return [], {"x": 0.0, "y": 0.0, "width": 1000.0, "height": 1000.0}
    min_x = min(float(point["x"]) for point in points)
    max_x = max(float(point["x"]) for point in points)
    min_y = min(float(point["y"]) for point in points)
    max_y = max(float(point["y"]) for point in points)
    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)
    padding = 70.0
    scale = min((1000.0 - padding * 2) / width, (1000.0 - padding * 2) / height)
    offset_x = (1000.0 - width * scale) / 2.0
    offset_y = (1000.0 - height * scale) / 2.0
    normalized = []
    for path in paths:
        normalized.append({
            **path,
            "points": [
                {"x": round((float(point["x"]) - min_x) * scale + offset_x, 3),
                 "y": round((float(point["y"]) - min_y) * scale + offset_y, 3)}
                for point in path.get("points", [])
            ],
        })
    return normalized, {"x": min_x, "y": min_y, "width": width, "height": height}


async def reconstruct_pattern(file: UploadFile) -> dict[str, Any]:
    analysis = await analyze_image(file)
    geometry = analysis["geometry"]
    if not geometry.get("points") and not geometry.get("circles") and not geometry.get("bezier_curves") and not geometry.get("polylines"):
        raise DotDetectionError("No pattern points were identified in the uploaded image.")

    grammar = analysis.get("grammar", {})
    grammar.setdefault(
        "construction_steps",
        [
            "Isolate dominant artwork region",
            "Detect structural primitives",
            "Validate candidate circles and curves",
            "Apply symmetry and repetition constraints",
            "Render clean parametric reconstruction",
        ],
    )
    symmetry = (analysis.get("symmetry") or {}).get("detected", [{}])[0]
    source_paths = geometry.get("paths", [])
    if not source_paths:
        source_paths = [path for path in valid_curves if len(path.get("points", [])) >= 2]
    faithful_paths, design_region = _normalize_paths(source_paths)
    valid_circles = [circle for circle in geometry.get("circles", []) if float(circle.get("confidence", 0)) >= 0.65][:8]
    valid_curves = (geometry.get("bezier_curves", []) + geometry.get("polylines", []))[:8]
    valid_lines = geometry.get("lines", [])[:8]

    svg_parts: list[str] = [
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000' width='100%' height='100%' preserveAspectRatio='xMidYMid meet'>",
        "<rect width='1000' height='1000' fill='#020817' />",
    ]

    for path in faithful_paths:
        d = _to_svg_path(path["points"], bool(path.get("closed")))
        svg_parts.append(f"<path d='{d}' fill='none' stroke='#fbbf24' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' opacity='0.9' />")

    svg_parts.append("</svg>")

    reconstruction = {
        "geometry": {
            "circles": valid_circles,
            "bezier_curves": valid_curves,
            "lines": valid_lines,
            "points": [],
            "paths": faithful_paths,
        },
        "status": "success",
        "image": {"width": analysis.get("measurements", {}).get("image_width", 0), "height": analysis.get("measurements", {}).get("image_height", 0)},
        "designRegion": design_region,
        "reconstruction": {"svg": "".join(svg_parts), "paths": faithful_paths},
        "grammar": grammar,
        "reconstructed_svg": "".join(svg_parts),
        "metrics": {
            "reconstruction_accuracy": "not available",
            "symmetry_match": float(symmetry.get("confidence", 0.0)) if isinstance(symmetry, dict) else "not available",
            "geometry_match": "not available",
            "curve_match": "not available",
        },
        "parameters": {
            "grid_rows": max(1, int((analysis.get("measurements") or {}).get("grid", {}).get("rows", 1))),
            "grid_columns": max(1, int((analysis.get("measurements") or {}).get("grid", {}).get("columns", 1))),
            "spacing": float((analysis.get("measurements") or {}).get("grid", {}).get("spacing", 40.0)),
            "symmetry_order": int((grammar.get("symmetry") or {}).get("order", 4)),
        },
        "analysis": analysis,
        "comparison": {
            "original_opacity": 0.75,
            "reconstruction_opacity": 0.9,
            "overlay_mode": True,
        },
    }
    return reconstruction
