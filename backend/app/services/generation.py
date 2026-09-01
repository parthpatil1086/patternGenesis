from __future__ import annotations

from math import cos, pi, sin
from typing import Any

from app.core.exceptions import PatternGenesisError


def _build_grid_geometry(rows: int, cols: int, spacing: float, symmetry_order: int) -> dict[str, Any]:
    points: list[dict[str, Any]] = []
    curves: list[dict[str, Any]] = []
    circles: list[dict[str, Any]] = []

    for row in range(rows):
        for col in range(cols):
            cx = col * spacing + spacing / 2
            cy = row * spacing + spacing / 2
            points.append({"id": f"p{row}-{col}", "x": cx, "y": cy})
            circles.append({
                "id": f"c{row}-{col}",
                "center": {"x": cx, "y": cy},
                "radius": spacing * 0.14,
                "type": "anchor",
            })
            curves.append({
                "id": f"curve{row}-{col}",
                "points": [
                    {"x": cx - spacing * 0.18, "y": cy},
                    {"x": cx, "y": cy - spacing * 0.28},
                    {"x": cx + spacing * 0.28, "y": cy},
                    {"x": cx, "y": cy + spacing * 0.18},
                ],
                "type": "bezier",
            })

    return {
        "points": points,
        "lines": [],
        "curves": curves,
        "circles": circles,
    }


def generate_pattern(grammar: dict[str, Any] | None = None, parameters: dict[str, Any] | None = None, variations: bool = False) -> dict[str, Any]:
    grammar = grammar or {"grammar_version": "1.0", "primitives": [], "parameters": {}}
    parameters = parameters or {}
    symmetry_order = int(parameters.get("symmetry_order", parameters.get("symmetryOrder", 4)))
    complexity = max(0.1, min(1.0, float(parameters.get("complexity", 0.65))))
    rows = int(parameters.get("grid_rows", parameters.get("gridRows", max(2, round(3 + complexity * 6)))))
    cols = int(parameters.get("grid_columns", parameters.get("gridColumns", max(2, round(3 + complexity * 6)))))
    spacing = float(parameters.get("spacing", 40))
    if symmetry_order < 1 or rows < 1 or cols < 1:
        raise PatternGenesisError("INVALID_PARAMETERS", "The generation parameters are invalid.", "Use positive integer values for grid and symmetry settings.")

    geometry = _build_grid_geometry(rows, cols, spacing, symmetry_order)
    geometry["svg"] = _geometry_to_svg(geometry)
    output = {
        "geometry": geometry,
        "grammar": {
            **grammar,
            "symmetry": {"type": "rotational", "order": symmetry_order},
            "repetition": {"count": rows * cols, "interval": spacing},
            "parameters": {**grammar.get("parameters", {}), **parameters},
        },
        "parameters": parameters,
        "metrics": {"primitive_count": len(geometry["points"]), "curve_count": len(geometry["curves"]), "circle_count": len(geometry["circles"]), "complexity": float(parameters.get("complexity", 1.0))},
    }
    if variations:
        output["variations"] = [
            {"id": "variant-simple", "parameters": {**parameters, "spacing": max(20.0, spacing * 0.8)}},
            {"id": "variant-complex", "parameters": {**parameters, "spacing": spacing * 1.2, "symmetry_order": symmetry_order + 1}},
        ]
    return output


def _instruction_parameters(instructions: str) -> dict[str, float]:
    text = instructions.lower()
    changes: dict[str, float] = {}
    if "more complex" in text or "complexity" in text and "increase" in text:
        changes["complexity"] = 0.85
    if "simpler" in text or "less complex" in text:
        changes["complexity"] = 0.3
    if "more symmetric" in text:
        changes["symmetry_order"] = 6.0
    if "less symmetric" in text or "asymmetric" in text:
        changes["symmetry_order"] = 1.0
    if "increase repetition" in text or "more repeated" in text:
        changes["repetition_count"] = 1.5
    if "decrease repetition" in text or "fewer repeated" in text:
        changes["repetition_count"] = 0.6
    if "denser" in text:
        changes["density"] = 0.85
    if "less dense" in text:
        changes["density"] = 0.35
    if "larger" in text:
        changes["scale"] = 1.2
    if "smaller" in text:
        changes["scale"] = 0.8
    if "increase spacing" in text:
        changes["spacing"] = 1.2
    if "decrease spacing" in text:
        changes["spacing"] = 0.8
    return changes


def _geometry_to_svg(geometry: dict[str, Any]) -> str:
    paths = geometry.get("paths", []) + geometry.get("curves", [])
    points = [point for path in paths for point in path.get("points", [])]
    points.extend(point for line in geometry.get("lines", []) for point in line.get("points", []))
    points.extend(circle.get("center", {}) for circle in geometry.get("circles", []))
    if not points:
        return "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000' />"
    min_x = min(float(point.get("x", 0)) for point in points)
    max_x = max(float(point.get("x", 0)) for point in points)
    min_y = min(float(point.get("y", 0)) for point in points)
    max_y = max(float(point.get("y", 0)) for point in points)
    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)
    pad = max(width, height) * 0.1
    parts = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='{min_x - pad} {min_y - pad} {width + 2 * pad} {height + 2 * pad}' preserveAspectRatio='xMidYMid meet'>"]
    for curve in paths:
        path = curve.get("points", [])
        if len(path) >= 2:
            d = "M " + " ".join(f"{point['x']} {point['y']}" for point in path)
            parts.append(f"<path d='{d}' fill='none' stroke='#34d399' stroke-width='2' stroke-linejoin='round' />")
    for circle in geometry.get("circles", []):
        center = circle.get("center", {})
        parts.append(f"<circle cx='{center.get('x', 0)}' cy='{center.get('y', 0)}' r='{circle.get('radius', 1)}' fill='none' stroke='#fbbf24' stroke-width='2' />")
    parts.append("</svg>")
    return "".join(parts)


def generate_from_analysis(
    analysis: dict[str, Any], parameters: dict[str, Any] | None = None, instructions: str = ""
) -> dict[str, Any]:
    """Create a new in-memory vector variation from analyzed reference paths."""
    parameters = {**(parameters or {}), **_instruction_parameters(instructions)}
    reference = analysis.get("geometry", {})
    reference_paths = reference.get("paths", [])
    if not reference_paths:
        raise PatternGenesisError("NO_REFERENCE_GEOMETRY", "The reference image did not yield vector paths.", "Try a clearer image or use text-only generation.")

    scale = float(parameters.get("scale", 1.0))
    if scale <= 0:
        raise PatternGenesisError("INVALID_PARAMETERS", "Scale must be positive.", "Use a scale greater than zero.")
    detail = max(0.1, min(1.0, float(parameters.get("detail", parameters.get("complexity", 0.7)))))
    density = max(0.1, min(1.0, float(parameters.get("density", 0.6))))
    path_limit = max(1, min(len(reference_paths), int(len(reference_paths) * density * (0.5 + detail))))
    curve_variation = max(0.0, min(1.0, float(parameters.get("curve_variation", 0.4))))
    all_points = [point for path in reference_paths for point in path.get("points", [])]
    center_x = sum(float(point["x"]) for point in all_points) / len(all_points)
    center_y = sum(float(point["y"]) for point in all_points) / len(all_points)
    generated_paths = []
    repeat_factor = max(1, min(3, int(round(float(parameters.get("repetition_count", 1)) / 8))) if "repetition_count" in parameters else 1)
    for copy_index in range(repeat_factor):
        copy_offset = (copy_index - (repeat_factor - 1) / 2.0) * max(1.0, (max(float(point["x"]) for point in all_points) - min(float(point["x"]) for point in all_points)) * 0.08)
        for path in reference_paths[: max(1, path_limit)]:
            generated_paths.append({
                **path,
                "id": f"generated_{path.get('id', len(generated_paths))}_{copy_index}",
                "points": [
                    {"x": center_x + (float(point["x"]) - center_x) * scale * (1 + curve_variation * 0.08) + copy_offset,
                     "y": center_y + (float(point["y"]) - center_y) * scale * (1 - curve_variation * 0.05)}
                    for point in path.get("points", [])
                ],
            })
    width = analysis.get("measurements", {}).get("image_width", 1000)
    height = analysis.get("measurements", {}).get("image_height", 1000)
    svg = _geometry_to_svg({"paths": generated_paths})
    return {
        "status": "success",
        "referenceGeometry": {"paths": reference_paths},
        "generatedGeometry": {"paths": generated_paths},
        "geometry": {"paths": generated_paths},
        "svg": svg,
        "grammar": analysis.get("grammar", {}),
        "parameters": parameters,
        "instructions": instructions,
        "metrics": {"reference_path_count": len(reference_paths), "generated_path_count": len(generated_paths)},
    }
