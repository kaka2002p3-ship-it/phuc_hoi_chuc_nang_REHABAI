"""Train/evaluate exercise-specific RehabCTR-TCN on real LOSO manifests.

This script does not fabricate phase or repetition labels. It evaluates the
available video-level Complete/Incomplete labels and explicitly reports that
rep-count/segmentation metrics are unavailable until boundary annotations exist.
"""
from __future__ import annotations
import argparse, json, random
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from training.exercise_specific_data import ExerciseSpecificDataset
from training.models.rehab_ctr_tcn import RehabCTRTCN


def seed(value):
    random.seed(value); np.random.seed(value); torch.manual_seed(value)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(value)


def evaluate(model, loader, device, include_predictions=False):
    model.eval(); ys=[]; ps=[]
    predictions=[]
    with torch.no_grad():
        for batch in loader:
            logits, _, _ = model(batch["joints"].to(device))
            ys.extend(batch["label"].numpy().astype(int).tolist())
            probabilities = torch.sigmoid(logits).cpu().numpy().tolist()
            labels = batch["label"].numpy().astype(int).tolist()
            predicted = [int(value >= .5) for value in probabilities]
            ps.extend(predicted)
            if include_predictions:
                predictions.extend({"sample_id": sample_id, "subject_id": subject_id, "label": label,
                                    "probability": round(float(probability), 6), "prediction": prediction}
                                   for sample_id, subject_id, label, probability, prediction in
                                   zip(batch["sample_id"], batch["subject_id"], labels, probabilities, predicted))
    if not ys: return {"sample_count": 0}
    majority = int(np.mean(ys) >= .5)
    metrics = {"sample_count": len(ys), "accuracy": float(accuracy_score(ys, ps)),
            "precision_macro": float(precision_score(ys, ps, average="macro", zero_division=0)),
            "recall_macro": float(recall_score(ys, ps, average="macro", zero_division=0)),
            "f1_macro": float(f1_score(ys, ps, average="macro", zero_division=0)),
            "majority_baseline_accuracy": float(accuracy_score(ys, [majority] * len(ys))),
            "majority_baseline_f1_macro": float(f1_score(ys, [majority] * len(ys), average="macro", zero_division=0)),
            "confusion_matrix": confusion_matrix(ys, ps, labels=[0, 1]).tolist(),
            "observed_classes": sorted(set(ys)), "predicted_classes": sorted(set(ps))}
    if include_predictions: metrics["predictions"] = predictions
    return metrics


def run_fold(args, fold, exercise, device):
    base = Path(args.project)
    manifests = base / "data" / "stage3_upper_limb" / "loso" / fold
    data_dir = base / "data" / "stage3_upper_limb" / "processed" / "keypoints"
    train = ExerciseSpecificDataset(manifests / "train_manifest.csv", data_dir, exercise, train=True)
    val = ExerciseSpecificDataset(manifests / "val_manifest.csv", data_dir, exercise)
    test = ExerciseSpecificDataset(manifests / "test_manifest.csv", data_dir, exercise)
    if not train or not val or not test or len(set(r["completion_label"] for r in test.records)) < 2:
        return {"fold_id": fold, "exercise": exercise, "status": "skipped_invalid_test_or_split",
                "counts": {"train": len(train), "val": len(val), "test": len(test)}}
    model = RehabCTRTCN(exercise, dropout=args.dropout).to(device)
    counts = np.bincount([int(float(r["completion_label"])) for r in train.records], minlength=2)
    weights = torch.tensor([1.0 / max(1, value) for value in counts], dtype=torch.float32, device=device)
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=weights[1] / weights[0])
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    train_loader = DataLoader(train, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val, batch_size=args.batch_size)
    test_loader = DataLoader(test, batch_size=args.batch_size)
    best_state, best_score, stale = None, -1.0, 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        for batch in train_loader:
            optimizer.zero_grad(set_to_none=True)
            logits, _, _ = model(batch["joints"].to(device))
            loss = criterion(logits, batch["label"].to(device))
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); optimizer.step()
        current = evaluate(model, val_loader, device); score = current.get("f1_macro", 0.0)
        if score > best_score:
            best_score = score; stale = 0; best_state = {k: v.detach().cpu().clone() for k,v in model.state_dict().items()}
        else: stale += 1
        print(f"[{exercise}][{fold}] epoch={epoch:03d} val_f1={score:.4f} val_n={current.get('sample_count',0)}", flush=True)
        if stale >= args.patience: break
    model.load_state_dict(best_state)
    metrics = evaluate(model, test_loader, device, include_predictions=True)
    checkpoint = Path(args.output) / exercise.lower() / f"{fold}.pth"
    checkpoint.parent.mkdir(parents=True, exist_ok=True); torch.save({"model": model.state_dict(), "exercise": exercise, "metrics": metrics}, checkpoint)
    return {"fold_id": fold, "exercise": exercise, "status": "complete", "counts": {"train":len(train),"val":len(val),"test":len(test)}, "metrics": metrics, "epochs": epoch, "checkpoint": str(checkpoint)}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--project", default=str(Path(__file__).resolve().parents[1])); parser.add_argument("--output", default="experiments/rehab_ctr_tcn"); parser.add_argument("--epochs", type=int, default=30); parser.add_argument("--patience", type=int, default=7); parser.add_argument("--batch-size", type=int, default=8); parser.add_argument("--lr", type=float, default=2e-4); parser.add_argument("--weight-decay", type=float, default=1e-4); parser.add_argument("--dropout", type=float, default=.3); parser.add_argument("--seed", type=int, default=42); parser.add_argument("--folds", default="all"); parser.add_argument("--exercises", default="HAND_OPENING,ELBOW_EXTENSION"); args=parser.parse_args(); seed(args.seed)
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu"); print(f"device={device}", flush=True)
    folds=[f"fold_{i:02d}" for i in range(1,11)] if args.folds == "all" else args.folds.split(',')
    results=[]
    for exercise in args.exercises.split(','):
        for fold in folds: results.append(run_fold(args, fold, exercise.strip(), device))
    out=Path(args.output); out.mkdir(parents=True, exist_ok=True); (out/"loso_results.json").write_text(json.dumps({"results":results,"protocol":"subject-wise LOSO","rep_metrics":"unavailable_without_rep_boundary_annotations","device":str(device)},indent=2),encoding="utf-8")
    done=[r for r in results if r["status"]=="complete"]; print(json.dumps({"complete_folds":len(done),"total_runs":len(results),"output":str(out/"loso_results.json")},indent=2))
if __name__ == "__main__": main()
