import os
import json
import argparse
import random
import platform
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import torch.optim as optim
from torch.utils.data import DataLoader
from shared.metrics import f1_score, accuracy_score
from training.device import select_training_device
from training.datasets.rehab_dataset import RehabDataset
from training.models.rehab_motionnet import RehabMotionNet
from training.model_registry import get_model
from training.checkpoint_utils import save_checkpoint, load_checkpoint_strict, get_checkpoint_path, compute_file_sha256
from scripts.generate_loso import hash_manifest
from training.monitoring import write_training_summary
from training.teacher_student import consistency_loss, pseudo_labels, validate_distillation_manifests

def train_proposed(args):
    seed = int(getattr(args, "seed", 42))
    gradient_accumulation = int(getattr(args, "gradient_accumulation", 2))
    gradient_clip = float(getattr(args, "gradient_clip", 1.0))
    amp_requested = bool(getattr(args, "amp", True))
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    upper_limb_only = getattr(args, "upper_limb_only", False)
    model_name = str(getattr(args, "model_name", "RehabMotionNet"))
    balanced_loss = getattr(args, "balanced_loss", False)
    checkpoint_root = getattr(args, "checkpoint_root", "training/checkpoints")
    pretrained_root = getattr(args, "pretrained_root", None) or checkpoint_root
    external_encoder_path = getattr(args, "external_encoder", None)
    ssl_encoder_path = getattr(args, "ssl_encoder", None)
    external_encoder_metadata = None
    run_root = getattr(args, "run_root", "training/runs")
    teacher_checkpoint = getattr(args, "teacher_checkpoint", None)
    distillation_weight = float(getattr(args, "distillation_weight", 0.25))
    confidence_threshold = float(getattr(args, "confidence_threshold", 0.90))
    student_noise_std = float(getattr(args, "student_noise_std", 0.005))
    distillation_temperature = float(getattr(args, "distillation_temperature", 2.0))
    device = select_training_device()
    print(f"Training {model_name} on {device} for {args.fold_id}")
    device_properties = torch.cuda.get_device_properties(device)
    runtime_metadata = {
        "python": platform.python_version(),
        "torch": str(torch.__version__),
        "torch_cuda_runtime": str(torch.version.cuda),
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_index": device.index,
        "cuda_device_name": device_properties.name,
        "gpu_vram_bytes": int(device_properties.total_memory),
        "cudnn_version": torch.backends.cudnn.version(),
        "amp_enabled": bool(amp_requested and device.type == "cuda"),
        "environment_profile": (
            "v3.1_canonical"
            if (
                platform.python_version() == "3.11.9"
                and str(torch.__version__).startswith("2.7.0")
                and str(torch.version.cuda) == "12.6"
            )
            else "noncanonical_exploratory"
        ),
    }
    print(f"[ENV] profile={runtime_metadata['environment_profile']}")
    
    if "extraction_quality" in args.train_manifest:
        raise ValueError("Cannot use extraction_quality.csv as a training manifest.")
        
    if not os.path.exists(args.norm_json):
        raise FileNotFoundError(f"Missing normalization JSON: {args.norm_json}")
        
    if not args.source_dir:
        raise ValueError("--source-dir is required in strict research mode")
    if teacher_checkpoint:
        validate_distillation_manifests(args.train_manifest, args.val_manifest, args.fold_id)
        
    # Read norm_schema FIRST before using it in strict loader
    with open(args.norm_json, 'r') as f:
        norm_schema = json.load(f)
        
    if norm_schema.get("metadata", {}).get("schema_version") != "1.1":
        raise ValueError("Invalid schema_version in normalization. Must be 1.1")
        
    prov_hash = norm_schema.get("metadata", {}).get("canonical_provenance_manifest_hash", "unknown")
    expected_train_hash = norm_schema.get("metadata", {}).get("canonical_train_manifest_hash", "unknown")
    
    # Load dataset
    data_dir = args.data_dir
    train_dataset = RehabDataset(data_dir=data_dir, source_dir=args.source_dir, split_manifest_csv=args.train_manifest, split='train', normalization_json=args.norm_json, fold_id=args.fold_id, apply_augmentation=True)
    val_dataset = RehabDataset(data_dir=data_dir, source_dir=args.source_dir, split_manifest_csv=args.val_manifest, split='val', normalization_json=args.norm_json, fold_id=args.fold_id, apply_augmentation=False)
    
    if len(train_dataset) == 0:
        raise ValueError("Train dataset is empty.")
    if len(val_dataset) == 0:
        raise ValueError("Val dataset is empty.")
        
    loader_generator = torch.Generator().manual_seed(seed)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, generator=loader_generator)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)
    
    # Check contrastive weights.  External multi-source pretraining is loaded
    # only through its explicit artifact path; the fold-specific checkpoint
    # remains the default and retains the strict fold provenance contract.
    ckpt_path = get_checkpoint_path(os.path.join(pretrained_root, args.fold_id), "RehabMotionNetEncoder", args.fold_id, "pretrained_encoder")
    is_ssl_adapter = model_name.lower() in {"optimizedssladapter", "optimized_ssl_adapter"}
    if is_ssl_adapter:
        if args.use_contrastive:
            raise ValueError("OptimizedSSLAdapter requires --no_contrastive; it has a separate frozen SSL branch")
        if external_encoder_path:
            raise ValueError("OptimizedSSLAdapter uses --ssl-encoder, not --external-encoder")
        if not ssl_encoder_path or not os.path.isfile(ssl_encoder_path):
            raise FileNotFoundError(f"IntelliRehab SSL encoder not found: {ssl_encoder_path}")
    elif ssl_encoder_path:
        raise ValueError("--ssl-encoder is only valid with OptimizedSSLAdapter")
    elif args.use_contrastive and external_encoder_path:
        if not os.path.isfile(external_encoder_path):
            raise FileNotFoundError(f"External encoder not found: {external_encoder_path}")
    elif args.use_contrastive and not os.path.exists(ckpt_path):
        raise FileNotFoundError(f"Missing pretrained encoder: {ckpt_path}. Cannot use contrastive learning.")
            
    # Model
    if is_ssl_adapter:
        model_config = {
            "num_exercises": 4,
            "adapter_dim": int(args.adapter_dim),
            "adapter_dropout": float(args.adapter_dropout),
        }
        architecture_signature = "optimized_v1_intellirehab_ssl_adapter_v1"
    elif model_name.lower() in {"externalencoderadapter", "external_adapter"}:
        if not args.use_contrastive:
            raise ValueError("ExternalEncoderAdapter requires the external encoder branch")
        if not external_encoder_path:
            raise ValueError("ExternalEncoderAdapter requires --external-encoder")
        model_config = {
            "num_exercises": 4,
            "adapter_dim": int(args.adapter_dim),
            "adapter_dropout": float(args.adapter_dropout),
        }
        architecture_signature = "external_encoder_adapter_v1"
    elif model_name.lower() in {"upperlimbctrgcn", "rehabmotionnetv3", "ctr_gcn"}:
        model_config = {
            "use_hand": args.use_hand,
            "use_kinematic": args.use_kinematic,
            "upper_limb_only": upper_limb_only,
        }
        architecture_signature = "upper_limb_ctr_gcn_v1"
        if args.use_contrastive:
            raise ValueError("CTR-GCN pilot requires --no_contrastive; its effect must be measured separately")
    else:
        model_config = {
            "use_hand": args.use_hand,
            "use_kinematic": args.use_kinematic,
            "use_contrastive": args.use_contrastive,
            "use_mstcn": args.use_mstcn,
            "use_attention": args.use_attention,
            "upper_limb_only": upper_limb_only,
        }
        architecture_signature = "rehab_motionnet_upper_limb_v2" if upper_limb_only else "rehab_motionnet_v1"
    model = get_model(model_name, config=model_config).to(device)

    if is_ssl_adapter:
        source_artifact = torch.load(ssl_encoder_path, map_location="cpu", weights_only=True)
        metadata = source_artifact.get("metadata", {})
        required_source_metadata = {
            "architecture_signature": "intellirehab_ssl_encoder_v1",
            "input_contract": "common_upper_limb_237_v1",
            "ontology_mapping_to_product": None,
            "source_fold": 0,
        }
        for key, expected in required_source_metadata.items():
            if metadata.get(key) != expected:
                raise ValueError(
                    f"IntelliRehab SSL metadata mismatch for {key}: "
                    f"expected {expected!r}, got {metadata.get(key)!r}"
                )
        if not metadata.get("manifest_sha256") or len(str(metadata["manifest_sha256"])) != 64:
            raise ValueError("IntelliRehab SSL manifest hash is missing or invalid")
        if metadata.get("source_datasets") != ["IntelliRehabDS"]:
            raise ValueError("IntelliRehab SSL source dataset contract mismatch")
        if "model_state_dict" not in source_artifact:
            raise KeyError("IntelliRehab SSL artifact is missing model_state_dict")
        model.ssl_encoder.load_state_dict(source_artifact["model_state_dict"], strict=True)
        model.freeze_encoder()
        external_encoder_metadata = {
            "artifact_sha256": compute_file_sha256(ssl_encoder_path),
            "manifest_sha256": str(metadata["manifest_sha256"]),
            "architecture_signature": str(metadata["architecture_signature"]),
            "input_contract": str(metadata["input_contract"]),
            "source_datasets": ["IntelliRehabDS"],
            "source_fold": 0,
            "ontology_mapping_to_product": None,
        }
        print(f"Loaded predeclared IntelliRehab SSL encoder: {ssl_encoder_path}")
    
    if args.use_contrastive:
        if external_encoder_path:
            external = torch.load(external_encoder_path, map_location="cpu", weights_only=True)
            metadata = external.get("metadata", {})
            allowed_external_signatures = {
                "external_multisource_encoder_v1",
                "datanew_ssl_encoder_v1",
            }
            if metadata.get("architecture_signature") not in allowed_external_signatures:
                raise ValueError("External encoder architecture signature mismatch")
            if metadata.get("ontology_mapping_to_product") is not None:
                raise ValueError("External encoder must not contain a coerced product-label mapping")
            if not metadata.get("manifest_sha256") or len(str(metadata["manifest_sha256"])) != 64:
                raise ValueError("External encoder manifest hash is missing or invalid")
            model.pretrained_encoder.load_state_dict(external["model_state_dict"], strict=True)
            external_encoder_metadata = {
                "artifact_sha256": compute_file_sha256(external_encoder_path),
                "manifest_sha256": str(metadata["manifest_sha256"]),
                "architecture_signature": str(metadata["architecture_signature"]),
                "source_datasets": list(metadata.get("source_datasets", [])),
                "ontology_mapping_to_product": None,
            }
            print(f"Loaded external multi-source encoder: {external_encoder_path}")
        else:
            # Load via strict checkpoint API
            load_checkpoint_strict(
                filepath=ckpt_path,
                model=model.pretrained_encoder,
                expected_model_id="RehabMotionNetEncoder",
                expected_fold_id=args.fold_id,
                expected_protocol="1.1",
                expected_provenance_hash=prov_hash,
                expected_train_manifest_hash=expected_train_hash,
                expected_normalization_hash=compute_file_sha256(args.norm_json),
                expected_class_mapping={0: "SSL"},
                # The SSL encoder artifact is a standalone full-input encoder.
                # Its metadata is independent of downstream ablation switches;
                # loading it with a disabled hand/attention branch would reject
                # a valid encoder or silently mix incompatible contracts.
                expected_model_config={"use_hand": True, "use_kinematic": True, "use_attention": True},
                expected_architecture_signature="rehab_motionnet_encoder_v1",
                expected_role="pretrained_encoder",
                device=device
            )
            print("Loaded pretrained_encoder weights safely via strict contract.")

        # ``no_grad`` protects the encoder weights, while requires_grad=False
        # also keeps them out of the optimizer.  Adapter models additionally
        # force the encoder's BatchNorm layers to eval mode in ``train()``.
        for parameter in model.pretrained_encoder.parameters():
            parameter.requires_grad_(False)
        if hasattr(model, "freeze_encoder"):
            model.freeze_encoder()

    teacher = None
    if teacher_checkpoint:
        teacher = RehabMotionNet(
            use_hand=args.use_hand,
            use_kinematic=args.use_kinematic,
            use_contrastive=args.use_contrastive,
            use_mstcn=args.use_mstcn,
            use_attention=args.use_attention,
            upper_limb_only=upper_limb_only,
        ).to(device)
        load_checkpoint_strict(
            filepath=teacher_checkpoint,
            model=teacher,
            expected_model_id="RehabMotionNet",
            expected_fold_id=args.fold_id,
            expected_protocol="1.1",
            expected_provenance_hash=prov_hash,
            expected_train_manifest_hash=expected_train_hash,
            expected_normalization_hash=compute_file_sha256(args.norm_json),
            expected_class_mapping={0: "Exercise_1", 1: "Exercise_2", 2: "Exercise_3", 3: "Exercise_4"},
            expected_model_config={
                "use_hand": args.use_hand,
                "use_kinematic": args.use_kinematic,
                "use_contrastive": args.use_contrastive,
                "use_mstcn": args.use_mstcn,
                "use_attention": args.use_attention,
                "upper_limb_only": upper_limb_only,
            },
            expected_architecture_signature="rehab_motionnet_upper_limb_v2" if upper_limb_only else "rehab_motionnet_v1",
            expected_role="supervised_model",
            device=device,
        )
        teacher.eval()
        for parameter in teacher.parameters():
            parameter.requires_grad_(False)
        print(f"Teacher-student enabled: threshold={confidence_threshold:.2f}, weight={distillation_weight:.2f}")
        
    if balanced_loss:
        counts = pd.Series(train_dataset.exercises).value_counts().reindex(range(4), fill_value=0).to_numpy()
        weights = counts.sum() / (4.0 * counts.clip(min=1))
        criterion_ex = nn.CrossEntropyLoss(weight=torch.tensor(weights, dtype=torch.float32, device=device))
        positives = float(sum(train_dataset.completions))
        negatives = float(len(train_dataset.completions) - positives)
        criterion_comp = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([negatives / max(positives, 1.0)], device=device))
    else:
        criterion_ex = nn.CrossEntropyLoss()
        criterion_comp = nn.BCEWithLogitsLoss()
    
    trainable_parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not trainable_parameters:
        raise ValueError("Model has no trainable target-domain parameters")
    optimizer = optim.AdamW(trainable_parameters, lr=args.lr, weight_decay=args.weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, args.epochs))
    amp_enabled = bool(amp_requested and device.type == "cuda")
    scaler = torch.amp.GradScaler("cuda", enabled=amp_enabled)
    
    os.makedirs(f"training/checkpoints/{args.fold_id}", exist_ok=True)
    # Start below the metric range so even a genuinely difficult fold with
    # Macro-F1 == 0 still produces a strict, provenance-bound checkpoint.
    best_f1 = float("-inf")
    history = []
    patience = getattr(args, "patience", 12)
    stale_epochs = 0
    
    
    df = pd.read_csv(args.train_manifest, dtype={"subject_id": str})
    current_train_hash = hash_manifest(df.to_dict('records'))
    if current_train_hash != expected_train_hash:
         raise ValueError(f"Train manifest hash mismatch. Expected {expected_train_hash}, got {current_train_hash}")
         
    norm_hash = compute_file_sha256(args.norm_json)
    
    for epoch in range(args.epochs):
        model.train()
        train_loss = 0.0
        pseudo_selected = 0
        pseudo_total = 0
        
        optimizer.zero_grad(set_to_none=True)
        for batch_idx, batch in enumerate(train_loader):
            x = batch["features"].to(device)
            y_ex = batch["exercise"].to(device)
            y_comp = batch["completion"].to(device).float().unsqueeze(1)
            
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=amp_enabled):
                student_x = x
                if teacher is not None and student_noise_std > 0:
                    student_x = x + torch.randn_like(x) * student_noise_std
                out_ex, out_comp = model(student_x)
                loss_ex = criterion_ex(out_ex, y_ex)
                mask = y_comp != -1
                loss = loss_ex + criterion_comp(out_comp[mask], y_comp[mask]) if mask.sum() > 0 else loss_ex
                if teacher is not None:
                    with torch.no_grad():
                        teacher_ex, _ = teacher(x)
                        _, _, selected = pseudo_labels(teacher_ex, confidence_threshold)
                    loss = loss + distillation_weight * consistency_loss(
                        out_ex, teacher_ex, confidence_threshold, distillation_temperature
                    )
                    pseudo_selected += int(selected.sum().item())
                    pseudo_total += int(selected.numel())

            raw_loss = loss.detach().item()
            scaler.scale(loss / gradient_accumulation).backward()
            should_step = (batch_idx + 1) % gradient_accumulation == 0 or (batch_idx + 1) == len(train_loader)
            if should_step:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), gradient_clip)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
            train_loss += raw_loss
            
        train_loss /= max(1, len(train_loader))
        scheduler.step()
        
        # Validation
        model.eval()
        val_loss = 0.0
        all_preds_ex = []
        all_labels_ex = []
        
        with torch.no_grad():
            for batch in val_loader:
                x = batch["features"].to(device)
                y_ex = batch["exercise"].to(device)
                y_comp = batch["completion"].to(device).float().unsqueeze(1)
                
                out_ex, out_comp = model(x)
                loss_ex = criterion_ex(out_ex, y_ex)
                mask = y_comp != -1
                if mask.sum() > 0:
                    loss_comp = criterion_comp(out_comp[mask], y_comp[mask])
                    loss = loss_ex + loss_comp
                else:
                    loss = loss_ex
                    
                val_loss += loss.item()
                preds = torch.argmax(out_ex, dim=1)
                all_preds_ex.extend(preds.cpu().numpy())
                all_labels_ex.extend(y_ex.cpu().numpy())
                
        val_loss /= max(1, len(val_loader))
        val_f1 = f1_score(all_labels_ex, all_preds_ex, average='macro', zero_division=0, labels=[0,1,2,3])
        train_preds = []
        train_labels = []
        # The train loop already consumed outputs; compute train F1 in a second
        # deterministic pass only when diagnostics are requested by the caller.
        if getattr(args, "diagnostics", True):
            model.eval()
            with torch.no_grad():
                for batch in train_loader:
                    logits, _ = model(batch["features"].to(device))
                    train_preds.extend(torch.argmax(logits, dim=1).cpu().numpy())
                    train_labels.extend(batch["exercise"].cpu().numpy())
        train_f1 = f1_score(train_labels, train_preds, average='macro', zero_division=0, labels=[0,1,2,3]) if train_labels else 0.0
        history.append({
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "train_f1": train_f1,
            "val_f1": val_f1,
            "teacher_student": teacher is not None,
            "pseudo_label_acceptance": pseudo_selected / max(1, pseudo_total),
            "confidence_threshold": confidence_threshold if teacher is not None else None,
            "distillation_temperature": distillation_temperature if teacher is not None else None,
            "learning_rate": optimizer.param_groups[0]["lr"],
        })
        
        print(f"Epoch {epoch+1}/{args.epochs} - Train Loss: {train_loss:.4f} - Val Loss: {val_loss:.4f} - Val F1: {val_f1:.4f}")
        
        if val_f1 > best_f1:
            best_f1 = val_f1
            stale_epochs = 0
            best_weights_path = get_checkpoint_path(os.path.join(checkpoint_root, args.fold_id), model_name, args.fold_id, "supervised_model")
            print("Validation F1 improved. Saving model.")
            save_checkpoint(
                model=model,
                optimizer=optimizer,
                epoch=epoch,
                filepath=best_weights_path,
                model_id=model_name,
                fold_id=args.fold_id,
                protocol_version="1.1",
                provenance_hash=prov_hash,
                train_manifest_hash=current_train_hash,
                normalization_hash=norm_hash,
                class_mapping={0: "Exercise_1", 1: "Exercise_2", 2: "Exercise_3", 3: "Exercise_4"},
                model_config=model_config,
                architecture_signature=architecture_signature,
                checkpoint_role="supervised_model",
                val_loss=val_loss,
                val_acc=val_f1,
                training_inputs={
                    "seed": seed,
                    "external_encoder": external_encoder_metadata,
                    "runtime": runtime_metadata,
                } if external_encoder_metadata else {"seed": seed, "runtime": runtime_metadata},
            )
        else:
            stale_epochs += 1
        if stale_epochs >= patience:
            print(f"Early stopping triggered after {patience} epochs without validation improvement.")
            break
            
    write_training_summary(
        os.path.join(run_root, f"{args.fold_id}_rehab_motionnet_summary.json"),
        history, model=model_name, fold_id=args.fold_id,
    )
    print(f"Finished training {model_name}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default="data/processed/keypoints")
    parser.add_argument("--train-manifest", type=str, required=True)
    parser.add_argument("--val-manifest", type=str, required=True)
    parser.add_argument("--norm-json", type=str, required=True)
    parser.add_argument("--fold-id", type=str, required=True)
    parser.add_argument("--model-name", default="RehabMotionNet")
    
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight_decay", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gradient-accumulation", type=int, default=2)
    parser.add_argument("--gradient-clip", type=float, default=1.0)
    parser.add_argument("--no-amp", action="store_false", dest="amp")
    parser.add_argument("--no-diagnostics", action="store_false", dest="diagnostics")
    
    # Ablation Hooks (default True)
    parser.add_argument("--no_hand", action="store_false", dest="use_hand")
    parser.add_argument("--no_kinematic", action="store_false", dest="use_kinematic")
    parser.add_argument("--no_contrastive", action="store_false", dest="use_contrastive")
    parser.add_argument("--no_mstcn", action="store_false", dest="use_mstcn")
    parser.add_argument("--no_attention", action="store_false", dest="use_attention")
    parser.add_argument("--upper-limb-only", action="store_true")
    parser.add_argument("--balanced-loss", action="store_true")
    parser.add_argument("--checkpoint-root", default="training/checkpoints")
    parser.add_argument("--pretrained-root", default=None)
    parser.add_argument("--external-encoder", default=None,
                        help="Optional validated multi-source encoder artifact from datasets 02/03")
    parser.add_argument("--ssl-encoder", default=None,
                        help="Predeclared fold-0 IntelliRehab self-supervised encoder")
    parser.add_argument("--adapter-dim", type=int, default=64)
    parser.add_argument("--adapter-dropout", type=float, default=0.20)
    parser.add_argument("--run-root", default="training/runs")
    parser.add_argument("--teacher-checkpoint", default=None)
    parser.add_argument("--distillation-weight", type=float, default=0.25)
    parser.add_argument("--confidence-threshold", type=float, default=0.90)
    parser.add_argument("--student-noise-std", type=float, default=0.005)
    parser.add_argument("--distillation-temperature", type=float, default=2.0)
    parser.add_argument("--source-dir", type=str, required=True)
    
    args = parser.parse_args()
    train_proposed(args)
