from __future__ import annotations

from typing import Any


def build_grammar(tradition: str = "kolam", *, points: list[dict[str, Any]] | None = None, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "grammar_version": "1.0",
        "tradition": tradition,
        "primitives": [{"type": "point", "count": len(points or [])}],
        "constraints": [],
        "transformations": [],
        "symmetry": {"type": "rotational", "order": int((parameters or {}).get("symmetry_order", 4))},
        "repetition": {"count": len(points or []), "interval": float((parameters or {}).get("spacing", 0.0))},
        "topology": {"nodes": len(points or []), "edges": 0},
        "parameters": parameters or {},
        "construction_steps": [
            "Create dot grid",
            "Establish symmetry",
            "Create base curve",
            "Apply transformation",
            "Repeat motif",
            "Close loops",
            "Finalize pattern",
        ],
        "metadata": {"source": "deterministic-kolam-grammar"},
    }
