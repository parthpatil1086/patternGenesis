import numpy as np

from app.kolam.detector import detect_kolam_dots


def test_detect_kolam_dots_on_synthetic_pattern():
    image = np.zeros((200, 200, 3), dtype=np.uint8)
    for x in range(20, 180, 40):
        for y in range(20, 180, 40):
            cv = (x, y)
            image[max(0, cv[1] - 3):min(200, cv[1] + 3), max(0, cv[0] - 3):min(200, cv[0] + 3)] = 255

    dots, grid = detect_kolam_dots(image)
    assert len(dots) >= 4
    assert grid["dot_count"] == len(dots)
    assert grid["rows"] >= 1
    assert grid["columns"] >= 1
