from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def detect_kolam_dots(image: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    dots: list[dict[str, Any]] = []
    for index, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area < 12:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        cx = float(x + w / 2)
        cy = float(y + h / 2)
        dots.append({
            "id": f"d{index}",
            "x": cx,
            "y": cy,
            "row": int(round(cy / max(h, 1))),
            "column": int(round(cx / max(w, 1))),
            "area": float(area),
        })

    dot_count = len(dots)
    rows = 1 if dot_count == 0 else len({d["row"] for d in dots})
    cols = 1 if dot_count == 0 else len({d["column"] for d in dots})
    grid = {
        "dot_count": dot_count,
        "rows": rows,
        "columns": cols,
        "grid_type": "square" if rows > 1 and cols > 1 else "single",
        "spacing": 0.0 if dot_count < 2 else float(np.mean([
            np.hypot(d1["x"] - d2["x"], d1["y"] - d2["y"]) for d1 in dots for d2 in dots if d1["id"] != d2["id"]
        ]) / max(len(dots) - 1, 1)),
    }
    return dots, grid
