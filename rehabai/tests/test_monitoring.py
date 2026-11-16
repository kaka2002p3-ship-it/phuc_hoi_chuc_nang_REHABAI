from training.monitoring import diagnose_history


def test_detects_overfitting_from_train_validation_history():
    history = [
        {"train_loss": 1.0, "val_loss": 1.0, "train_f1": 0.55, "val_f1": 0.55},
        {"train_loss": 0.5, "val_loss": 1.1, "train_f1": 0.85, "val_f1": 0.50},
        {"train_loss": 0.3, "val_loss": 1.2, "train_f1": 0.95, "val_f1": 0.45},
    ]
    result = diagnose_history(history)
    assert result["status"] == "warning"
    assert any("OVERFITTING" in warning for warning in result["warnings"])


def test_detects_underfitting_when_both_streams_are_low():
    history = [
        {"train_loss": 1.0, "val_loss": 1.1, "train_f1": 0.30, "val_f1": 0.25},
        {"train_loss": 0.95, "val_loss": 1.0, "train_f1": 0.35, "val_f1": 0.30},
        {"train_loss": 0.9, "val_loss": 0.95, "train_f1": 0.40, "val_f1": 0.35},
    ]
    result = diagnose_history(history)
    assert any("UNDERFITTING" in warning for warning in result["warnings"])
