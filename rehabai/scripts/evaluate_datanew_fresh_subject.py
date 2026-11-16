"""Inference-only evaluation for a locked, never-trained-on datanew manifest.

The script refuses video overlap with the supplied training manifests. Labels
are optional: without labels it writes predictions for later expert review;
with labels it writes metrics. It never updates checkpoints or production.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from torch.utils.data import DataLoader, Dataset

from training.datanew_rep_dataset import normalize_hand, normalize_elbow
from training.exercise_specific_data import _best_hand
from training.models.rehab_ctr_tcn import RehabCTRTCN
from shared.preprocessing.sequence import resample_sequence


class FreshRepDataset(Dataset):
    def __init__(self, table, catalog, exercise, target_frames):
        cat = pd.read_csv(catalog, dtype={"sample_id": str})
        self.rows = table[table.exercise.eq(exercise)].merge(
            cat[["sample_id", "output"]], left_on="video_id", right_on="sample_id",
            how="left", validate="many_to_one"
        ).to_dict("records")
        self.exercise, self.target_frames = exercise, target_frames

    def __len__(self): return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        output = Path(str(row["output"]))
        if not output.is_file(): raise FileNotFoundError(output)
        start, end = max(0, int(float(row["start_frame"]))), min(95, int(float(row["end_frame"])))
        with np.load(output, allow_pickle=False) as data:
            value = (normalize_hand(_best_hand(data["left_hand_landmarks"], data["right_hand_landmarks"]))
                     if self.exercise == "HAND_OPENING" else normalize_elbow(data["pose_landmarks"]))
        value = value[start:end + 1]
        if len(value) < 2: raise ValueError(f"Invalid window {row['video_id']}/{row['rep_id']}")
        value = resample_sequence(value, self.target_frames).astype(np.float32)
        return {"joints": torch.from_numpy(value), "index": index}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--catalog", type=Path, required=True)
    ap.add_argument("--checkpoint-dir", type=Path, required=True)
    ap.add_argument("--known-split-dir", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--target-frames", type=int, default=48)
    ap.add_argument("--batch-size", type=int, default=32)
    args = ap.parse_args()

    table = pd.read_csv(args.manifest, dtype={"video_id": str})
    required = {"video_id", "rep_id", "exercise", "start_frame", "end_frame"}
    missing = required - set(table.columns)
    if missing: raise SystemExit(f"BLOCKED missing columns: {sorted(missing)}")
    if table.duplicated(["video_id", "rep_id"]).any(): raise SystemExit("BLOCKED duplicate video_id/rep_id")
    known = set()
    for split_dir in args.known_split_dir:
        for split in ("train", "val", "test"):
            path = split_dir / f"{split}_manifest.csv"
            if path.is_file(): known |= set(pd.read_csv(path, dtype={"video_id": str}).video_id)
    overlap = known & set(table.video_id)
    if overlap: raise SystemExit(f"BLOCKED fresh manifest overlaps {len(overlap)} known videos")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    output_rows, metrics = [], {}
    for exercise in sorted(table.exercise.unique()):
        part = table[table.exercise.eq(exercise)].reset_index(drop=True)
        dataset = FreshRepDataset(part, args.catalog, exercise, args.target_frames)
        loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False)
        seed_predictions = []
        for checkpoint in sorted(args.checkpoint_dir.glob("datanew_rep_temporal_second_review_v2_seed*/")):
            seed = checkpoint.name.rsplit("seed", 1)[-1]
            path = checkpoint / f"{exercise.lower()}.pth"
            if not path.is_file(): continue
            saved = torch.load(path, map_location="cpu", weights_only=False)
            model = RehabCTRTCN(exercise).to(device); model.load_state_dict(saved["model"]); model.eval()
            probs = []
            with torch.no_grad():
                for batch in loader:
                    logits, _, _ = model(batch["joints"].to(device)); probs.extend(torch.sigmoid(logits).cpu().numpy())
            seed_predictions.append((seed, np.asarray(probs), float(saved["threshold"])))
        if not seed_predictions: raise SystemExit(f"No checkpoints found for {exercise}")
        mean_prob = np.mean([item[1] for item in seed_predictions], axis=0)
        majority_pred = np.asarray([
            int(sum(int(prob[i] >= threshold) for _, prob, threshold in seed_predictions) >= (len(seed_predictions) + 1) // 2)
            for i in range(len(part))
        ])
        for i, row in part.iterrows():
            values = {f"prob_correct_seed{seed}": float(prob[i]) for seed, prob, _ in seed_predictions}
            votes = [int(prob[i] >= threshold) for _, prob, threshold in seed_predictions]
            item = {**row.to_dict(), **values, "mean_prob_correct": float(mean_prob[i]),
                    "majority_prediction": "correct" if sum(votes) >= (len(votes) + 1) // 2 else "incorrect",
                    "shadow_only": True}
            output_rows.append(item)
        if "completion_label" in part.columns:
            y = (part.completion_label == "correct").astype(int).to_numpy()
            pred = majority_pred
            metrics[exercise] = {"rows": len(y), "accuracy": float(accuracy_score(y, pred)),
                "f1_macro": float(f1_score(y, pred, average="macro", zero_division=0)),
                "confusion_matrix": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
                "report": classification_report(y, pred, labels=[0, 1], target_names=["incorrect", "correct"], output_dict=True, zero_division=0)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(output_rows).to_csv(args.output, index=False, encoding="utf-8-sig")
    report = {"status": "complete", "mode": "inference_only_shadow", "device": str(device),
              "known_split_dirs": [str(x) for x in args.known_split_dir], "metrics": metrics,
              "warning": "Shadow predictions do not alter production or user-visible results."}
    args.output.with_suffix(".metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": "complete", "output": str(args.output.resolve()), "metrics": metrics}, indent=2))


if __name__ == "__main__": main()
