from src.predictions import demo_rule_predict, predict_from_reading


def test_demo_rule_is_labeled() -> None:
    result = demo_rule_predict(20.0, 0.0, threshold=35.0)
    assert result.required is True
    assert result.source == "demo_rule"
    assert "not a machine-learning prediction" in result.explanation.lower()


def test_invalid_reading_does_not_recommend_irrigation() -> None:
    result = predict_from_reading({"soil_moisture": 10, "rainfall_mm": 0, "valid": False})
    assert result.label == "Unavailable"
    assert result.required is False
