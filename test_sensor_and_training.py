from src.data_processing import validate_sensor_frame
from src.model_training import train_and_compare
from src.sensor_simulator import generate_sample_dataset, irrigation_label


def test_sample_dataset_has_both_classes() -> None:
    frame = generate_sample_dataset(days=3, freq_minutes=30)
    assert set(frame["source"].unique()) == {"demo"}
    assert frame["irrigation_required"].nunique() == 2
    expected = [
        irrigation_label(row.soil_moisture, row.rainfall_mm)
        for row in frame.itertuples()
    ]
    assert list(frame["irrigation_required"]) == expected


def test_training_returns_measured_metrics() -> None:
    frame = validate_sensor_frame(generate_sample_dataset(days=4), require_target=True)
    training = train_and_compare(frame, test_size=0.25)
    assert training["best_name"] in {"Decision Tree", "Random Forest", "Logistic Regression"}
    for result in training["results"]:
        assert 0.0 <= result.accuracy <= 1.0
        assert result.n_test > 0
        assert result.n_train > result.n_test
        assert len(result.confusion) == 2
