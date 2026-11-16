import os
import torch
import hashlib
from typing import Dict, Any, Optional


def _safe_torch_load(filepath: str, device: str = "cpu"):
    """Load an internal checkpoint with a version-compatible safe policy.

    PyTorch 2.5 serializes ``Optimizer.state_dict`` step counters as
    ``TorchVersion`` in some runs.  The checkpoint is still tensor/primitive
    data produced by our own writer; explicitly allowlisting that value keeps
    the default weights-only protection without falling back to arbitrary
    object unpickling.
    """
    try:
        return torch.load(filepath, map_location=device, weights_only=True)
    except Exception as exc:
        message = str(exc)
        if "torch.torch_version.TorchVersion" not in message:
            raise
        try:
            from torch.torch_version import TorchVersion
            add_safe_globals = getattr(torch.serialization, "add_safe_globals", None)
            if add_safe_globals is None:
                raise
            add_safe_globals([TorchVersion])
            return torch.load(filepath, map_location=device, weights_only=True)
        except Exception:
            raise exc

def compute_file_sha256(filepath: str) -> str:
    """Compute SHA256 of a file."""
    if not os.path.exists(filepath):
        return ""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def is_valid_sha256(s: str) -> bool:
    return bool(s and isinstance(s, str) and len(s) == 64 and all(c in '0123456789abcdefABCDEF' for c in s))

def get_checkpoint_path(output_dir: str, model_id: str, fold_id: str, checkpoint_role: str) -> str:
    """Unified path resolver for all trainers and evaluators."""
    return os.path.join(output_dir, f"{model_id}_{fold_id}_{checkpoint_role}.pth")

def save_checkpoint(
    model: torch.nn.Module, 
    optimizer: torch.optim.Optimizer, 
    epoch: int, 
    filepath: str,
    model_id: str,
    fold_id: str,
    protocol_version: str,
    provenance_hash: str,
    train_manifest_hash: str,
    normalization_hash: str,
    class_mapping: Dict[int, str],
    model_config: Dict[str, Any],
    architecture_signature: str,
    checkpoint_role: str,
    val_loss: Optional[float] = None,
    val_acc: Optional[float] = None,
    training_inputs: Optional[Dict[str, Any]] = None,
):
    """
    Save a model checkpoint with strict research metadata contract.
    Ensures that the resulting file embeds exactly the environment it was trained in.
    """
    
    # 1. Enforce required metadata fields
    if not model_id:
        raise ValueError("model_id is required for checkpointing")
    if not fold_id:
        raise ValueError("fold_id is required for checkpointing")
    if protocol_version != "1.1":
        raise ValueError(f"protocol_version must be 1.1, got {protocol_version}")
    if not is_valid_sha256(provenance_hash):
        raise ValueError("provenance_hash is required and must be a 64-char SHA256 string")
    if not is_valid_sha256(train_manifest_hash):
         raise ValueError("train_manifest_hash is required and must be a 64-char SHA256 string")
    if not is_valid_sha256(normalization_hash):
         raise ValueError("normalization_hash is required and must be a 64-char SHA256 string")
    if not class_mapping or len(class_mapping) == 0:
         raise ValueError("class_mapping is required and must not be empty")
    if not model_config:
         raise ValueError("model_config is required")
    if not architecture_signature:
         raise ValueError("architecture_signature is required")
    if not checkpoint_role:
         raise ValueError("checkpoint_role is required")

    checkpoint = {
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict() if optimizer else None,
        'val_loss': val_loss,
        'val_acc': val_acc,
        'metadata': {
            'model_id': model_id,
            'fold_id': fold_id,
            'protocol_version': protocol_version,
            'provenance_hash': provenance_hash,
            'train_manifest_hash': train_manifest_hash,
            'normalization_hash': normalization_hash,
            'class_mapping': class_mapping,
            'model_config': model_config,
            'architecture_signature': architecture_signature,
            'checkpoint_role': checkpoint_role
        }
    }
    if training_inputs is not None:
        checkpoint['metadata']['training_inputs'] = training_inputs
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Save safely to temporary file then rename (atomic save)
    tmp_path = filepath + ".tmp"
    torch.save(checkpoint, tmp_path)
    os.replace(tmp_path, filepath)

def load_checkpoint_strict(
    filepath: str, 
    model: torch.nn.Module, 
    expected_model_id: str,
    expected_fold_id: str,
    expected_protocol: str,
    expected_provenance_hash: str,
    expected_train_manifest_hash: str,
    expected_normalization_hash: str,
    expected_class_mapping: Dict[int, str],
    expected_model_config: Dict[str, Any],
    expected_architecture_signature: str,
    expected_role: str,
    device: str = "cpu"
) -> Dict[str, Any]:
    """
    Load a checkpoint and strictly verify its embedded metadata against the expected environment.
    Prevents loading models from the wrong fold, wrong data version, or wrong normalization schema.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Checkpoint not found: {filepath}")
        
    checkpoint = _safe_torch_load(filepath, device=device)
    
    if 'metadata' not in checkpoint:
        raise KeyError(f"Checkpoint {filepath} is missing the required 'metadata' block. Likely a legacy file.")
        
    metadata = checkpoint['metadata']
    
    # Missing hashes check
    if not expected_provenance_hash or not expected_train_manifest_hash or not expected_normalization_hash:
         raise ValueError("Expected hashes cannot be None in strict research mode.")
         
    # Check strict invariants
    if metadata.get('protocol_version') != expected_protocol:
         raise ValueError(f"Checkpoint protocol mismatch: expected {expected_protocol}, got {metadata.get('protocol_version')}")
         
    if metadata.get('model_id') != expected_model_id:
         raise ValueError(f"Checkpoint model_id mismatch: expected {expected_model_id}, got {metadata.get('model_id')}")

    if metadata.get('fold_id') != expected_fold_id:
         raise ValueError(f"Checkpoint fold mismatch: expected {expected_fold_id}, got {metadata.get('fold_id')}")
         
    if metadata.get('provenance_hash') != expected_provenance_hash:
         raise ValueError(f"Checkpoint provenance hash mismatch! Expected {expected_provenance_hash}, got {metadata.get('provenance_hash')}")
         
    if metadata.get('train_manifest_hash') != expected_train_manifest_hash:
         raise ValueError(f"Checkpoint train manifest hash mismatch! Expected {expected_train_manifest_hash}, got {metadata.get('train_manifest_hash')}")
         
    if metadata.get('normalization_hash') != expected_normalization_hash:
         raise ValueError(f"Checkpoint normalization hash mismatch! Expected {expected_normalization_hash}, got {metadata.get('normalization_hash')}")
         
    if metadata.get('class_mapping') != expected_class_mapping:
         raise ValueError(f"Checkpoint class mapping mismatch! Expected {expected_class_mapping}, got {metadata.get('class_mapping')}")
         
    if metadata.get('model_config') != expected_model_config:
         raise ValueError(f"Checkpoint model config mismatch! Expected {expected_model_config}, got {metadata.get('model_config')}")
         
    if metadata.get('architecture_signature') != expected_architecture_signature:
         raise ValueError(f"Checkpoint architecture signature mismatch! Expected {expected_architecture_signature}, got {metadata.get('architecture_signature')}")
         
    if metadata.get('checkpoint_role') != expected_role:
         raise ValueError(f"Checkpoint role mismatch! Expected {expected_role}, got {metadata.get('checkpoint_role')}")

    model.load_state_dict(checkpoint['model_state_dict'])
    
    return checkpoint
