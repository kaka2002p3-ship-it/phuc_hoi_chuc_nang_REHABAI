import os
import json
import torch
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

from training.device import select_training_device
from training.datasets.ssl_dataset import SSLRehabDataset
from training.models.shared_encoder import SharedMotionEncoder
from training.models.contrastive import SimCLR, NTXentLoss
from training.checkpoint_utils import save_checkpoint, get_checkpoint_path

def pretrain_model(data_dir, source_dir, train_manifest, norm_json, fold_id, epochs=100, batch_size=32, lr=1e-3):
    device = select_training_device()
    print(f"Pretraining Shared Motion Encoder on {device} for fold {fold_id}")
    
    if not os.path.exists(norm_json):
        raise FileNotFoundError(f"Missing normalization schema: {norm_json}")
        
    if "extraction_quality" in train_manifest:
        raise ValueError("Cannot use extraction_quality.csv for SSL pretraining.")

    # Dataset and Loader
    if not source_dir:
        raise ValueError("source_dir is required in strict mode")
    dataset = SSLRehabDataset(data_dir=data_dir, source_dir=source_dir, train_manifest_csv=train_manifest, normalization_json=norm_json, fold_id=fold_id)
    
    if len(dataset) < 2:
        raise ValueError("SSL pretraining requires at least 2 REAL_VERIFIED train samples; dummy fallback is forbidden.")
            
    # Batch size shouldn't exceed dataset size, but needs to be >= 2 for contrastive
    bs = min(batch_size, len(dataset))
    if bs < 2:
        # Fallback for dry-run
        bs = len(dataset)
        
    loader = DataLoader(dataset, batch_size=bs, shuffle=True, drop_last=True if len(dataset) >= bs*2 else False)
    
    if len(loader) == 0:
        print("Loader empty after drop_last.")
        loader = DataLoader(dataset, batch_size=bs, shuffle=True, drop_last=False)
        if len(loader) == 0: return
    
    # Model
    encoder = SharedMotionEncoder()
    model = SimCLR(encoder)
    model = model.to(device)
    
    criterion = NTXentLoss(temperature=0.1)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    writer = SummaryWriter(log_dir=f"training/runs/pretrain_simclr_{fold_id}")
    os.makedirs(f"training/checkpoints/{fold_id}", exist_ok=True)
    
    best_loss = float('inf')
    
    # Extract norm_hash and verify
    with open(norm_json, 'r') as f:
        norm_schema = json.load(f)
        
    if norm_schema.get("metadata", {}).get("schema_version") != "1.1":
        raise ValueError("Invalid schema_version in normalization. Must be 1.1")
        
    prov_hash = norm_schema.get("metadata", {}).get("canonical_provenance_manifest_hash", "unknown")
    expected_train_hash = norm_schema.get("metadata", {}).get("canonical_train_manifest_hash", "unknown")
    
    # Calculate current train manifest hash
    import pandas as pd
    from scripts.generate_loso import hash_manifest
    from training.checkpoint_utils import compute_file_sha256, save_checkpoint, get_checkpoint_path
    
    df = pd.read_csv(train_manifest, dtype={"subject_id": str})
    current_train_hash = hash_manifest(df.to_dict('records'))
    if current_train_hash != expected_train_hash:
         raise ValueError(f"Train manifest hash mismatch. Expected {expected_train_hash}, got {current_train_hash}")
         
    norm_hash = compute_file_sha256(norm_json)
    
    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        
        for view1, view2 in loader:
            view1 = view1.to(device)
            view2 = view2.to(device)
            
            # If batch size is 1, NTXentLoss will crash (cannot contrast). Skip batch.
            if view1.shape[0] < 2:
                continue
                
            optimizer.zero_grad()
            z_i, z_j = model(view1, view2)
            
            loss = criterion(z_i, z_j)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            
        epoch_loss /= max(1, len(loader))
        scheduler.step()
        
        writer.add_scalar("Loss/Contrastive", epoch_loss, epoch)
        print(f"Epoch {epoch+1}/{epochs} - Contrastive Loss: {epoch_loss:.4f}")
        
        if epoch_loss < best_loss and epoch_loss > 0: # >0 check for 1-sample fallback
            best_loss = epoch_loss
            # Save only the encoder
            ckpt_path = get_checkpoint_path(f"training/checkpoints/{fold_id}", "RehabMotionNetEncoder", fold_id, "pretrained_encoder")
            save_checkpoint(
                model=encoder,
                optimizer=optimizer,
                epoch=epoch,
                filepath=ckpt_path,
                model_id="RehabMotionNetEncoder",
                fold_id=fold_id,
                protocol_version="1.1",
                provenance_hash=prov_hash,
                train_manifest_hash=current_train_hash,
                normalization_hash=norm_hash,
                class_mapping={0: "SSL"}, # No classes for SSL, but need a mock mapping
                model_config={"use_hand": True, "use_kinematic": True, "use_attention": True}, # Default full config for encoder
                architecture_signature="rehab_motionnet_encoder_v1",
                checkpoint_role="pretrained_encoder",
                val_loss=epoch_loss, # Use train loss for tracking
                val_acc=None
            )
            print("Encoder weights saved.")
    writer.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="data/processed/keypoints")
    parser.add_argument("--train-manifest", type=str, required=True)
    parser.add_argument("--norm-json", type=str, required=True)
    parser.add_argument("--fold-id", type=str, required=True)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--source-dir", type=str, required=True)
    args = parser.parse_args()
    
    pretrain_model(
        data_dir=args.data_dir,
        source_dir=args.source_dir,
        train_manifest=args.train_manifest,
        norm_json=args.norm_json,
        fold_id=args.fold_id,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr
    )
