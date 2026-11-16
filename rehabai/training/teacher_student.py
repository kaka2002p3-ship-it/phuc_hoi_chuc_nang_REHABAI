"""Teacher-student utilities with fail-closed pseudo-label selection.

Pseudo-labels are generated only from a teacher trained on the fold's train
partition.  Validation/test samples are never accepted by this helper.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import torch

@torch.no_grad()
def pseudo_labels(logits: torch.Tensor, confidence_threshold: float = 0.90):
    probs = torch.softmax(logits, dim=-1)
    confidence, labels = probs.max(dim=-1)
    mask = confidence >= confidence_threshold
    return labels, confidence, mask

def consistency_loss(student_logits: torch.Tensor, teacher_logits: torch.Tensor,
                     confidence_threshold: float = 0.90,
                     temperature: float = 2.0) -> torch.Tensor:
    """Confidence-masked soft-target knowledge distillation loss."""
    _, _, mask = pseudo_labels(teacher_logits.detach(), confidence_threshold)
    if not bool(mask.any()):
        return student_logits.sum() * 0.0
    teacher_prob = torch.softmax(teacher_logits[mask].detach() / temperature, dim=-1)
    student_log_prob = torch.log_softmax(student_logits[mask] / temperature, dim=-1)
    return torch.nn.functional.kl_div(student_log_prob, teacher_prob, reduction="batchmean") * temperature**2


def validate_distillation_manifests(train_manifest: str, val_manifest: str, fold_id: str) -> None:
    """Reject split or subject leakage before a teacher-student run starts."""
    train = pd.read_csv(Path(train_manifest), dtype={"subject_id": str})
    val = pd.read_csv(Path(val_manifest), dtype={"subject_id": str})
    required = {"sample_id", "subject_id", "fold_id", "split"}
    for name, frame, expected_split in (("train", train, "train"), ("val", val, "val")):
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{name} manifest missing columns: {sorted(missing)}")
        if set(frame["split"].astype(str)) != {expected_split}:
            raise ValueError(f"{name} manifest contains a non-{expected_split} record")
        if set(frame["fold_id"].astype(str)) != {fold_id}:
            raise ValueError(f"{name} manifest contains another fold")
    if set(train["sample_id"]) & set(val["sample_id"]):
        raise ValueError("Teacher-student sample leakage between train and validation")
    if set(train["subject_id"]) & set(val["subject_id"]):
        raise ValueError("Teacher-student subject leakage between train and validation")
