from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Point:
    x: float
    y: float
    id: str | None = None


@dataclass
class Line:
    p0: Point
    p1: Point
    id: str | None = None


@dataclass
class Circle:
    center: Point
    radius: float
    id: str | None = None


@dataclass
class BezierCurve:
    points: list[Point]
    id: str | None = None


@dataclass
class Grid:
    rows: int
    columns: int
    spacing: float
    origin: Point = field(default_factory=lambda: Point(0, 0))
    id: str | None = None


@dataclass
class GeometryCollection:
    points: list[Point] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)
    circles: list[Circle] = field(default_factory=list)
    curves: list[BezierCurve] = field(default_factory=list)
    grids: list[Grid] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "points": [
                {"id": p.id, "x": p.x, "y": p.y} for p in self.points
            ],
            "lines": [
                {"id": l.id, "p0": {"x": l.p0.x, "y": l.p0.y}, "p1": {"x": l.p1.x, "y": l.p1.y}}
                for l in self.lines
            ],
            "circles": [
                {"id": c.id, "center": {"x": c.center.x, "y": c.center.y}, "radius": c.radius}
                for c in self.circles
            ],
            "curves": [
                {"id": c.id, "points": [{"x": p.x, "y": p.y} for p in c.points]}
                for c in self.curves
            ],
            "grids": [
                {"id": g.id, "rows": g.rows, "columns": g.columns, "spacing": g.spacing}
                for g in self.grids
            ],
        }
