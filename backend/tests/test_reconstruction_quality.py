import io

import numpy as np
from fastapi import UploadFile

from app.services.analysis import analyze_image
from app.services.reconstruction import reconstruct_pattern


def _make_synthetic_pattern_image() -> bytes:
    image = np.full((420, 420, 3), 255, dtype=np.uint8)

    cv2 = __import__("cv2")
    for radius in (30, 70, 110):
        cv2.circle(image, (210, 210), radius, (0, 0, 0), 2)

    cv2.line(image, (60, 120), (350, 220), (0, 0, 0), 2)
    cv2.line(image, (80, 300), (330, 120), (0, 0, 0), 2)
    cv2.ellipse(image, (130, 130), (45, 25), 0, 0, 360, (0, 0, 0), 2)
    cv2.ellipse(image, (290, 300), (55, 20), 30, 0, 360, (0, 0, 0), 2)

    _, buffer = cv2.imencode(".png", image)
    return buffer.tobytes()


def test_analyze_image_extracts_real_geometry_from_synthetic_pattern():
    image_bytes = _make_synthetic_pattern_image()
    file = UploadFile(filename="synthetic.png", file=io.BytesIO(image_bytes), headers={"content-type": "image/png"})

    result = __import__("asyncio").run(analyze_image(file))
    geometry = result["geometry"]

    assert len(geometry.get("points", [])) >= 3
    assert len(geometry.get("circles", [])) >= 1
    assert len(geometry.get("bezier_curves", [])) + len(geometry.get("lines", [])) >= 1


def test_reconstruction_uses_detected_geometry_in_svg():
    image_bytes = _make_synthetic_pattern_image()
    file = UploadFile(filename="synthetic.png", file=io.BytesIO(image_bytes), headers={"content-type": "image/png"})

    result = __import__("asyncio").run(reconstruct_pattern(file))
    svg = result["reconstructed_svg"]

    assert "<svg" in svg.lower()
    assert "path" in svg.lower() or "circle" in svg.lower() or "ellipse" in svg.lower()
