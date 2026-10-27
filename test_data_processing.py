import pandas as pd
import pytest

from src.data_processing import DataValidationError, validate_sensor_frame


def test_valid_frame_is_accepted() -> None:
    frame = pd.DataFrame(
        {
            "soil_moisture": [40.0, 22.0],
            "soil_temperature": [24.0, 25.0],
            "air_temperature": [30.0, 31.0],
            "humidity": [55.0, 60.0],
            "rainfall_mm": [0.0, 0.2],
            "irrigation_required": [0, 1],
        }
    )
    cleaned = validate_sensor_frame(frame, require_target=True)
    assert len(cleaned) == 2


def test_missing_columns_raise() -> None:
    frame = pd.DataFrame({"soil_moisture": [40.0]})
    with pytest.raises(DataValidationError, match="Missing required columns"):
        validate_sensor_frame(frame)


def test_bad_target_raises() -> None:
    frame = pd.DataFrame(
        {
            "soil_moisture": [40.0, 22.0],
            "soil_temperature": [24.0, 25.0],
            "air_temperature": [30.0, 31.0],
            "humidity": [55.0, 60.0],
            "rainfall_mm": [0.0, 0.2],
            "irrigation_required": [2, 1],
        }
    )
    with pytest.raises(DataValidationError, match="0/1"):
        validate_sensor_frame(frame, require_target=True)
