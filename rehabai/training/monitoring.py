"""Training-history and generalization diagnostics.

Diagnostics are based only on train/validation streams.  The test fold is never
read here, so model selection cannot leak test information.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


def diagnose_history(history: Sequence[Mapping[str, float]], *, min_epochs: int = 3) -> dict[str, Any]:
    if not history:
        return {"status": "insufficient_data", "warnings": [], "generalization_gap": None}
    train_f1 = [float(row["train_f1"]) for row in history if "train_f1" in row]
    val_f1 = [float(row["val_f1"]) for row in history if "val_f1" in row]
    train_loss = [float(row["train_loss"]) for row in history if "train_loss" in row]
    val_loss = [float(row["val_loss"]) for row in history if "val_loss" in row]
    warnings: list[str] = []
    gap = (train_f1[-1] - val_f1[-1]) if train_f1 and val_f1 else None
    if len(history) >= min_epochs and train_f1 and val_f1:
        recent = min(3, len(history))
        train_rising = train_f1[-1] >= train_f1[-recent]
        val_falling = val_f1[-1] < val_f1[-recent]
        loss_diverging = bool(train_loss and val_loss and val_loss[-1] > val_loss[-recent])
        if gap is not None and gap >= 0.15 and train_rising and (val_falling or loss_diverging):
            warnings.append("OVERFITTING: train F1 rises while validation deteriorates.")
        if train_f1[-1] < 0.60 and val_f1[-1] < 0.60:
            warnings.append("UNDERFITTING: both train and validation F1 remain low.")
    return {
        "status": "warning" if warnings else "ok",
        "warnings": warnings,
        "generalization_gap": gap,
        "best_val_f1": max(val_f1) if val_f1 else None,
        "best_epoch": (max(range(len(val_f1)), key=val_f1.__getitem__) + 1) if val_f1 else None,
    }


def write_training_summary(path: str | Path, history: Sequence[Mapping[str, float]], **metadata: Any) -> dict[str, Any]:
    summary = {"history": list(history), "diagnostics": diagnose_history(history), **metadata}
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
