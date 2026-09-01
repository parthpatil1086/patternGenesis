from app.services.generation import generate_pattern


def test_generate_pattern_returns_real_geometry():
    result = generate_pattern(
        {"grammar_version": "1.0", "tradition": "kolam"},
        {"symmetry_order": 4, "grid_rows": 3, "grid_columns": 3, "spacing": 40},
    )

    geometry = result["geometry"]
    assert len(geometry["points"]) >= 9
    assert len(geometry["circles"]) >= 1
    assert len(geometry["curves"]) >= 1
    assert result["grammar"]["symmetry"]["order"] == 4
