import os
import time
import argparse
from pathlib import Path
import torch
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
import torch.optim as optim
from shared.metrics import accuracy_score, f1_score, precision_score, recall_score
import numpy as np
from tqdm import tqdm

from training.device import select_training_device
from training.datasets.rehab_dataset import RehabDataset
from training.models.cnn_transformer import RehabModel
from training.losses.focal_loss import FocalLoss

def train_one_epoch(model, dataloader, criterion, optimizer, scaler, device):
    model.train()
    running_loss = 0.0
    all_preds = []
    all_labels = []
    
    pbar = tqdm(dataloader, desc="Training")
    for batch in pbar:
        features = batch['features'].to(device)
        labels = batch['exercise'].to(device)
        
        optimizer.zero_grad()
        
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type=='cuda'):
            outputs = model(features)
            loss = criterion(outputs, labels)
            
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        
        running_loss += loss.item()
        
        preds = torch.argmax(outputs, dim=1).cpu().numpy()
        all_preds.extend(preds)
        all_labels.extend(labels.cpu().numpy())
        
        pbar.set_postfix({"loss": f"{loss.item():.4f}"})
        
    epoch_loss = running_loss / len(dataloader)
    acc = accuracy_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    
    return epoch_loss, acc, f1

def validate(model, dataloader, criterion, device):
    model.eval()
    running_loss = 0.0
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Validation"):
            features = batch['features'].to(device)
            labels = batch['exercise'].to(device)
            
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type=='cuda'):
                outputs = model(features)
                loss = criterion(outputs, labels)
                
            running_loss += loss.item()
            
            preds = torch.argmax(outputs, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(labels.cpu().numpy())
            
    epoch_loss = running_loss / len(dataloader)
    acc = accuracy_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    precision = precision_score(all_labels, all_preds, average='macro', zero_division=0)
    recall = recall_score(all_labels, all_preds, average='macro', zero_division=0)
    
    return epoch_loss, acc, f1, precision, recall

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="data/processed/keypoints")
    parser.add_argument("--train-manifest", type=str, required=True, help="Path to train_manifest.csv")
    parser.add_argument("--val-manifest", type=str, required=True, help="Path to val_manifest.csv")
    parser.add_argument("--norm-json", type=str, required=True, help="Path to fold normalization JSON")
    parser.add_argument("--fold-id", type=str, required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--source-dir", type=str, required=True, help="Path to source video directory")
    parser.add_argument("--num-classes", type=int, default=4,
                        help="Number of exercise classes in the manifest (default: 4)")
    args = parser.parse_args()

    device = select_training_device()
    print(f"Using device: {device}")
    
    if "extraction_quality" in args.train_manifest:
        raise ValueError("Cannot use extraction_quality.csv as a training manifest.")
        
    if not os.path.exists(args.norm_json):
        raise FileNotFoundError(f"Missing normalization JSON: {args.norm_json}")

    # Create datasets
    train_dataset = RehabDataset(
        data_dir=args.data_dir, 
        source_dir=args.source_dir, 
        split_manifest_csv=args.train_manifest, 
        split='train', 
        normalization_json=args.norm_json, 
        fold_id=args.fold_id, 
        apply_augmentation=True
    )
    val_dataset = RehabDataset(
        data_dir=args.data_dir, 
        source_dir=args.source_dir, 
        split_manifest_csv=args.val_manifest, 
        split='val', 
        normalization_json=args.norm_json, 
        fold_id=args.fold_id, 
        apply_augmentation=False
    )
            
    if len(train_dataset) == 0:
        raise ValueError("Train dataset is empty.")
    if len(val_dataset) == 0:
        raise ValueError("Val dataset is empty.")
        
    print(f"Train size: {len(train_dataset)}, Val size: {len(val_dataset)}")
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, 
                              num_workers=min(4, os.cpu_count() or 1), pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, 
                            num_workers=min(4, os.cpu_count() or 1), pin_memory=True)
    
    if args.num_classes < 2:
        raise ValueError("--num-classes must be at least 2")
    num_classes = args.num_classes
    print(f"Number of classes: {num_classes}")
    
    model = RehabModel(num_classes=num_classes).to(device)
    
    criterion = FocalLoss(gamma=2.0)
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    scaler = torch.cuda.amp.GradScaler(enabled=device.type=='cuda')
    
    writer = SummaryWriter(log_dir=f"data/models/logs/{args.fold_id}_cnn_transformer")
    save_dir = Path(f"data/models/weights/{args.fold_id}")
    save_dir.mkdir(parents=True, exist_ok=True)
    
    best_f1 = 0.0
    
    # Extract norm_hash and verify
    import json
    with open(args.norm_json, 'r') as f:
        norm_schema = json.load(f)
        
    if norm_schema.get("metadata", {}).get("schema_version") != "1.1":
        raise ValueError("Invalid schema_version in normalization. Must be 1.1")
        
    prov_hash = norm_schema.get("metadata", {}).get("provenance_manifest_hash", "unknown")
    expected_train_hash = norm_schema.get("metadata", {}).get("canonical_train_manifest_hash", "unknown")
    
    # Calculate current train manifest hash
    import pandas as pd
    from scripts.generate_loso import hash_manifest
    from training.checkpoint_utils import compute_file_sha256, save_checkpoint, get_checkpoint_path
    
    df = pd.read_csv(args.train_manifest, dtype={"subject_id": str})
    current_train_hash = hash_manifest(df.to_dict('records'))
    if current_train_hash != expected_train_hash:
         raise ValueError(f"Train manifest hash mismatch. Expected {expected_train_hash}, got {current_train_hash}")
         
    norm_hash = compute_file_sha256(args.norm_json)
    
    for epoch in range(args.epochs):
        print(f"\nEpoch {epoch+1}/{args.epochs}")
        
        train_loss, train_acc, train_f1 = train_one_epoch(model, train_loader, criterion, optimizer, scaler, device)
        val_loss, val_acc, val_f1, val_prec, val_rec = validate(model, val_loader, criterion, device)
        
        scheduler.step()
        
        # Logging
        writer.add_scalar("Loss/Train", train_loss, epoch)
        writer.add_scalar("Loss/Val", val_loss, epoch)
        writer.add_scalar("Metric/Train_F1", train_f1, epoch)
        writer.add_scalar("Metric/Val_F1", val_f1, epoch)
        
        print(f"Train - Loss: {train_loss:.4f}, Acc: {train_acc:.4f}, F1: {train_f1:.4f}")
        print(f"Val   - Loss: {val_loss:.4f}, Acc: {val_acc:.4f}, F1: {val_f1:.4f}, Prec: {val_prec:.4f}, Rec: {val_rec:.4f}")
        
        if val_f1 >= best_f1:
            best_f1 = val_f1
            best_weights_path = get_checkpoint_path(str(save_dir), "RehabModel", args.fold_id, "supervised_model")
            save_checkpoint(
                model=model,
                optimizer=optimizer,
                epoch=epoch,
                filepath=best_weights_path,
                model_id="RehabModel",
                fold_id=args.fold_id,
                protocol_version="1.1",
                provenance_hash=prov_hash,
                train_manifest_hash=current_train_hash,
                normalization_hash=norm_hash,
                class_mapping={index: f"Exercise_{index + 1}" for index in range(num_classes)},
                model_config={"num_classes": num_classes},
                architecture_signature="cnn_transformer_v1",
                checkpoint_role="supervised_model",
                val_loss=val_loss,
                val_acc=val_f1
            )
            print("Saved new best model!")
            
    writer.close()
    print("Training complete.")

if __name__ == "__main__":
    main()
