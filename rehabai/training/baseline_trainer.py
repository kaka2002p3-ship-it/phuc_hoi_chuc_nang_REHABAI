import os
import json
import argparse
import random
import platform
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from shared.metrics import f1_score, accuracy_score
from torch.utils.tensorboard import SummaryWriter

from training.datasets.rehab_dataset import RehabDataset
from training.device import select_training_device
from training.model_registry import get_model
from training.checkpoint_utils import save_checkpoint, get_checkpoint_path
from training.monitoring import write_training_summary

class EarlyStopping:
    def __init__(self, patience=10, mode='max'):
        self.patience = patience
        self.mode = mode
        self.best_score = -float('inf') if mode == 'max' else float('inf')
        self.counter = 0
        self.early_stop = False

    def __call__(self, score):
        if self.mode == 'max':
            if score > self.best_score:
                self.best_score = score
                self.counter = 0
                return True
            else:
                self.counter += 1
        else:
            if score < self.best_score:
                self.best_score = score
                self.counter = 0
                return True
            else:
                self.counter += 1
                
        if self.counter >= self.patience:
            self.early_stop = True
        return False


def train_baseline(args):
    seed = int(getattr(args, "seed", 42))
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    import numpy as np
    np.random.seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    device = select_training_device()
    print(f"Training {args.model} on {device} for {args.fold_id}")
    
    if not os.path.exists(args.norm_json):
        raise FileNotFoundError(f"Missing normalization JSON: {args.norm_json}")
    
    model_config = {"input_dim": 237, "num_exercises": 4}
    if args.model == "lstm":
        model_config.update({"hidden_size": args.hidden_size, "num_layers": args.num_layers, "bidirectional": False})
    model = get_model(args.model, model_config).to(device)
    
    if not args.source_dir:
        raise ValueError("--source-dir is required in strict research mode")
    train_ds = RehabDataset(
        data_dir=args.data_dir, 
        source_dir=args.source_dir, 
        split_manifest_csv=args.train_manifest, 
        split="train", 
        normalization_json=args.norm_json, 
        fold_id=args.fold_id, 
        apply_augmentation=True
    )
    val_ds = RehabDataset(
        data_dir=args.data_dir, 
        source_dir=args.source_dir, 
        split_manifest_csv=args.val_manifest, 
        split="val", 
        normalization_json=args.norm_json, 
        fold_id=args.fold_id, 
        apply_augmentation=False
    )
    
    train_bs = min(args.batch_size, len(train_ds)) if len(train_ds) > 0 else args.batch_size
    val_bs = min(args.batch_size, len(val_ds)) if len(val_ds) > 0 else args.batch_size
    
    train_loader = DataLoader(train_ds, batch_size=train_bs, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=val_bs, shuffle=False)
    
    criterion_ex = nn.CrossEntropyLoss()
    criterion_comp = nn.BCEWithLogitsLoss()
    
    optimizer = optim.AdamW(model.parameters(), lr=args.lr)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=5)
    
    early_stopping = EarlyStopping(patience=args.patience, mode='max')
    history = []
    
    run_root = getattr(args, "run_root", "training/runs")
    checkpoint_root = getattr(args, "checkpoint_root", "training/checkpoints")
    writer = SummaryWriter(log_dir=os.path.join(run_root, f"{args.fold_id}_baseline_{args.model}"))
    
    best_weights_path = get_checkpoint_path(os.path.join(checkpoint_root, args.fold_id), args.model, args.fold_id, "supervised_model")
    os.makedirs(os.path.join(checkpoint_root, args.fold_id), exist_ok=True)
    
    # Extract norm_hash and verify
    with open(args.norm_json, 'r') as f:
        norm_schema = json.load(f)
        
    if norm_schema.get("metadata", {}).get("schema_version") != "1.1":
        raise ValueError("Invalid schema_version in normalization. Must be 1.1")
        
    prov_hash = norm_schema.get("metadata", {}).get("canonical_provenance_manifest_hash", "unknown")
    expected_train_hash = norm_schema.get("metadata", {}).get("canonical_train_manifest_hash", "unknown")
    
    # Calculate current train manifest hash
    import pandas as pd
    from scripts.generate_loso import hash_manifest
    from training.checkpoint_utils import compute_file_sha256, save_checkpoint
    
    df = pd.read_csv(args.train_manifest, dtype={"subject_id": str})
    current_train_hash = hash_manifest(df.to_dict('records'))
    if current_train_hash != expected_train_hash:
         raise ValueError(f"Train manifest hash mismatch. Expected {expected_train_hash}, got {current_train_hash}")
         
    norm_hash = compute_file_sha256(args.norm_json)
    
    best_saved = False
    for epoch in range(args.epochs):
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            x = batch["features"].to(device)
            y_ex = batch["exercise"].to(device)
            y_comp = batch["completion"].to(device).unsqueeze(1) # (B, 1)
            
            optimizer.zero_grad()
            out_ex, out_comp = model(x)
            
            loss_ex = criterion_ex(out_ex, y_ex)
            loss_comp = criterion_comp(out_comp, y_comp)
            loss = loss_ex + loss_comp
            
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            
        train_loss /= max(1, len(train_loader))
        
        # Validation
        val_loss = 0.0
        val_macro_f1 = 0.0
        
        model.eval()
        all_preds_ex = []
        all_labels_ex = []
        all_preds_comp = []
        all_labels_comp = []
        
        with torch.no_grad():
            for batch in val_loader:
                x = batch["features"].to(device)
                y_ex = batch["exercise"].to(device)
                y_comp = batch["completion"].to(device).unsqueeze(1)
                
                out_ex, out_comp = model(x)
                
                loss_ex = criterion_ex(out_ex, y_ex)
                loss_comp = criterion_comp(out_comp, y_comp)
                loss = loss_ex + loss_comp
                val_loss += loss.item()
                
                preds_ex = torch.argmax(out_ex, dim=1).cpu().numpy()
                preds_comp = (torch.sigmoid(out_comp) > 0.5).float().cpu().numpy()
                
                all_preds_ex.extend(preds_ex)
                all_labels_ex.extend(y_ex.cpu().numpy())
                all_preds_comp.extend(preds_comp)
                all_labels_comp.extend(y_comp.cpu().numpy())
        
        val_loss /= max(1, len(val_loader))
        
        f1_ex = f1_score(all_labels_ex, all_preds_ex, average='macro', zero_division=0, labels=[0,1,2,3])
        f1_comp = f1_score(all_labels_comp, all_preds_comp, average='macro', zero_division=0, labels=[0,1])
        val_macro_f1 = (f1_ex + f1_comp) / 2.0
        train_f1_ex = 0.0
        train_f1_comp = 0.0
        if getattr(args, "diagnostics", True):
            model.eval()
            train_preds, train_labels = [], []
            train_comp_preds, train_comp_labels = [], []
            with torch.no_grad():
                for batch in train_loader:
                    out_ex, out_comp = model(batch["features"].to(device))
                    train_preds.extend(torch.argmax(out_ex, dim=1).cpu().numpy())
                    train_labels.extend(batch["exercise"].cpu().numpy())
                    train_comp_preds.extend((torch.sigmoid(out_comp) > 0.5).float().cpu().numpy())
                    train_comp_labels.extend(batch["completion"].unsqueeze(1).cpu().numpy())
            train_f1_ex = f1_score(train_labels, train_preds, average='macro', zero_division=0, labels=[0,1,2,3]) if train_labels else 0.0
            train_f1_comp = f1_score(train_comp_labels, train_comp_preds, average='macro', zero_division=0, labels=[0,1]) if train_comp_labels else 0.0
        train_macro_f1 = (train_f1_ex + train_f1_comp) / 2.0
        history.append({"epoch": epoch + 1, "train_loss": train_loss, "val_loss": val_loss, "train_f1": train_macro_f1, "val_f1": val_macro_f1})
        
        scheduler.step(val_macro_f1)
        
        writer.add_scalar("Loss/Val", val_loss, epoch)
        writer.add_scalar("Macro_F1/Val", val_macro_f1, epoch)
        writer.add_scalar("Loss/Train", train_loss, epoch)
        
        print(f"Epoch {epoch+1}/{args.epochs} - Train Loss: {train_loss:.4f} - Val Loss: {val_loss:.4f} - Val F1: {val_macro_f1:.4f}")
        
        if early_stopping(val_macro_f1):
            print("Validation F1 improved. Saving model.")
            save_checkpoint(
                model=model,
                optimizer=optimizer,
                epoch=epoch,
                filepath=best_weights_path,
                model_id=args.model,
                fold_id=args.fold_id,
                protocol_version="1.1",
                provenance_hash=prov_hash,
                train_manifest_hash=current_train_hash,
                normalization_hash=norm_hash,
                class_mapping={0: "Exercise_1", 1: "Exercise_2", 2: "Exercise_3", 3: "Exercise_4"},
                model_config=model_config,
                architecture_signature=f"baseline_{args.model}_v1",
                checkpoint_role="supervised_model",
                val_loss=val_loss,
                val_acc=val_macro_f1,
                training_inputs={
                    "seed": seed,
                    "runtime": {
                        "python": platform.python_version(),
                        "torch": str(torch.__version__),
                        "torch_cuda_runtime": str(torch.version.cuda),
                        "cuda_device_name": torch.cuda.get_device_name(device),
                        "environment_profile": (
                            "v3.1_canonical" if str(torch.__version__).startswith("2.7.0")
                            and str(torch.version.cuda) == "12.6" else "noncanonical_exploratory"
                        ),
                    },
                },
            )
            best_saved = True
            
        if early_stopping.early_stop:
            print(f"Early stopping triggered at epoch {epoch+1}.")
            break
            
    if not best_saved:
        raise RuntimeError("Baseline training completed without a checkpoint")
    write_training_summary(
        os.path.join(run_root, f"{args.fold_id}_baseline_{args.model}_summary.json"),
        history, model=args.model, fold_id=args.fold_id,
    )
    writer.close()
    print(f"Finished training {args.model}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default="data/processed/keypoints")
    parser.add_argument("--model", type=str, required=True, choices=["mlp", "lstm", "bilstm", "tcn", "stgcn"])
    parser.add_argument("--train-manifest", type=str, required=True)
    parser.add_argument("--val-manifest", type=str, required=True)
    parser.add_argument("--norm-json", type=str, required=True)
    parser.add_argument("--fold-id", type=str, required=True)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--source-dir", type=str, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--num-layers", type=int, default=1)
    parser.add_argument("--checkpoint-root", default="training/checkpoints")
    parser.add_argument("--run-root", default="training/runs")
    parser.add_argument("--no-diagnostics", action="store_false", dest="diagnostics")
    args = parser.parse_args()
    
    train_baseline(args)
