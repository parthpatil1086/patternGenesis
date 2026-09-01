from app.services.generation import generate_pattern


def test_generate_pattern_returns_full_geometry_contract():
    result = generate_pattern(
        {"grammar_version": "1.0", "tradition": "kolam"},
        {"symmetry_order": 4, "grid_rows": 3, "grid_columns": 3, "spacing": 40},
    )

    geometry = result["geometry"]
    assert geometry["points"]
    assert geometry["circles"]
    assert geometry["curves"]
    assert result["grammar"]["symmetry"]["order"] == 4
    assert result["metrics"]["circle_count"] == len(geometry["circles"])
