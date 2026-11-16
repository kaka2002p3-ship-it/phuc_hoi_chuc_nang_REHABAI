"""Build a read-only second-review queue from temporal multi-seed disagreement.

This script never changes expert labels. Model disagreement is only a reason to
inspect the source clip again, not evidence that the expert label is wrong.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from training.datanew_rep_dataset import DatanewRepDataset
from training.models.rehab_ctr_tcn import RehabCTRTCN


def load_checkpoint(path: Path, device: torch.device):
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    model = RehabCTRTCN("ELBOW_FLEXION").to(device)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    return model, float(checkpoint["threshold"])


def probabilities(model, loader, device: torch.device) -> np.ndarray:
    output = []
    with torch.no_grad():
        for batch in loader:
            logits, _, _ = model(batch["joints"].to(device))
            output.extend(torch.sigmoid(logits).cpu().numpy().tolist())
    return np.asarray(output, dtype=np.float64)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split-dir", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--experiments-dir", type=Path, default=Path("experiments"))
    parser.add_argument("--seeds", default="42,7,2026")
    parser.add_argument("--target-frames", type=int, default=48)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rows = []

    for split in ("train", "val", "test"):
        manifest = args.split_dir / f"{split}_manifest.csv"
        dataset = DatanewRepDataset(
            manifest, args.catalog, "ELBOW_FLEXION", args.target_frames
        )
        loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False)
        table = pd.DataFrame(dataset.rows).drop(columns=["sample_id", "output"], errors="ignore")
        if "split" in table.columns:
            table["split"] = split
            columns = ["split"] + [c for c in table.columns if c != "split"]
            table = table[columns]
        else:
            table.insert(0, "split", split)

        decisions = []
        margins = []
        for seed in seeds:
            checkpoint = (
                args.experiments_dir
                / f"datanew_rep_temporal_seed{seed}"
                / "elbow_flexion.pth"
            )
            model, threshold = load_checkpoint(checkpoint, device)
            probability = probabilities(model, loader, device)
            decision = (probability >= threshold).astype(np.int64)
            table[f"prob_correct_seed{seed}"] = np.round(probability, 6)
            table[f"threshold_seed{seed}"] = threshold
            table[f"prediction_seed{seed}"] = np.where(decision == 1, "correct", "incorrect")
            decisions.append(decision)
            margins.append(np.abs(probability - threshold))
            del model

        votes = np.stack(decisions, axis=1)
        margin = np.stack(margins, axis=1)
        correct_votes = votes.sum(axis=1)
        majority = (correct_votes >= (len(seeds) // 2 + 1)).astype(np.int64)
        truth = (table["completion_label"].to_numpy() == "correct").astype(np.int64)
        vote_disagreement = (correct_votes > 0) & (correct_votes < len(seeds))
        majority_wrong = majority != truth
        missed_incorrect = (truth == 0) & (majority == 1)
        disputed_correct = (truth == 1) & (majority == 0)
        near_threshold = margin.min(axis=1) <= 0.08

        table["correct_votes"] = correct_votes
        table["majority_prediction"] = np.where(majority == 1, "correct", "incorrect")
        table["vote_disagreement"] = vote_disagreement
        table["majority_disagrees_with_label"] = majority_wrong
        table["min_threshold_margin"] = np.round(margin.min(axis=1), 6)

        priority = np.full(len(table), 99, dtype=np.int64)
        reason = np.full(len(table), "", dtype=object)
        priority[missed_incorrect] = 1
        reason[missed_incorrect] = "expert_incorrect_but_majority_predicts_correct"
        mask = disputed_correct & (priority == 99)
        priority[mask] = 2
        reason[mask] = "expert_correct_but_majority_predicts_incorrect"
        mask = vote_disagreement & (priority == 99)
        priority[mask] = 3
        reason[mask] = "seeds_disagree"
        mask = near_threshold & (priority == 99)
        priority[mask] = 4
        reason[mask] = "prediction_near_seed_threshold"
        table["review_priority"] = priority
        table["suspicion_reason"] = reason
        table["second_review_label"] = ""
        table["second_review_notes"] = ""
        rows.append(table[priority < 99])

    queue = pd.concat(rows, ignore_index=True)
    split_rank = queue["split"].map({"test": 0, "val": 1, "train": 2})
    queue = queue.assign(_split_rank=split_rank).sort_values(
        ["review_priority", "_split_rank", "video_id", "rep_id"]
    ).drop(columns="_split_rank")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(args.output, index=False, encoding="utf-8-sig")

    print(f"device={device}")
    print(f"output={args.output.resolve()}")
    print(f"flagged_rows={len(queue)}")
    print(queue.groupby(["review_priority", "suspicion_reason"]).size().to_string())
    print("No expert labels were changed.")


if __name__ == "__main__":
    main()
