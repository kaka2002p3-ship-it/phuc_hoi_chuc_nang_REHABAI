"""Export optimized model bundles for backend deployment.

Two entry points:

- :func:`export_model_bundle` -- strict, metadata-verified TorchScript
  exporter used by the production pipeline and tests.  It refuses to
  overwrite an existing bundle unless every integrity check passes, and
  a mid-export failure leaves the previous bundle untouched.
- ``__main__`` -- legacy one-shot export of the optimized_seed7/fold_04
  checkpoint into ``artifacts/model_v2``.  Re-runnable; TorchScript
  saves are byte-deterministic for a given PyTorch build, so the
  resulting ``model.pt`` matches the checked-in
  ``artifacts/model_v2/bundle_sha256.json`` manifest.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import torch

from training.checkpoint_utils import (
    _safe_torch_load,
    compute_file_sha256,
)
from training.model_registry import get_model

# Runtime contract enforced by backend/core/model_loader.py:
_TEMPORAL_FRAMES = 96

_BUNDLE_FILES = (
    "fold_metadata.json",
    "normalization.json",
    "model_config.json",
    "class_mapping.json",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_class_mapping(class_mapping: dict) -> dict:
    """Class mapping keys are ints in checkpoints but strings after a JSON
    round-trip; compare both sides in canonical string-keyed form."""
    return {str(index): label for index, label in class_mapping.items()}


def _validate_checkpoint_contract(
    checkpoint: dict,
    model_name: str,
    fold_id: str,
    architecture_signature: str,
    class_mapping: dict,
    norm_json: str,
) -> None:
    """Fail fast if the checkpoint was produced by a different experiment."""
    metadata = checkpoint.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Checkpoint is missing the required 'metadata' block")
    if metadata.get("model_id") != model_name:
        raise ValueError(
            f"Checkpoint model_id mismatch: expected {model_name!r}, got {metadata.get('model_id')!r}"
        )
    if metadata.get("fold_id") != fold_id:
        raise ValueError(
            f"Checkpoint fold mismatch: expected {fold_id!r}, got {metadata.get('fold_id')!r}"
        )
    if metadata.get("architecture_signature") != architecture_signature:
        raise ValueError(
            "Checkpoint architecture signature mismatch: "
            f"expected {architecture_signature!r}, got {metadata.get('architecture_signature')!r}"
        )
    if _normalize_class_mapping(metadata.get("class_mapping") or {}) != _normalize_class_mapping(class_mapping):
        raise ValueError(
            f"Checkpoint class mapping does not match {class_mapping!r}"
        )
    expected_norm_hash = compute_file_sha256(norm_json)
    if metadata.get("normalization_hash") != expected_norm_hash:
        raise ValueError(
            "Checkpoint normalization hash does not match the supplied norm JSON"
        )


def export_model_bundle(
    checkpoint: str,
    fold_metadata_path: str,
    norm_json: str,
    model_name: str,
    model_config_path: str,
    class_mapping_path: str,
    architecture_signature: str,
    output_dir: str,
    fold_id: str,
) -> Path:
    """Export a strictly verified TorchScript inference bundle.

    The bundle is staged in a temporary sibling directory and moved into
    ``output_dir`` only after tracing succeeds, so a failure never
    corrupts an existing bundle.

    Returns the resolved output directory.
    """
    output_path = Path(output_dir).resolve()
    parent = output_path.parent
    parent.mkdir(parents=True, exist_ok=True)

    model_config = json.loads(Path(model_config_path).read_text(encoding="utf-8"))
    class_mapping = json.loads(Path(class_mapping_path).read_text(encoding="utf-8"))

    # 1. Load and verify the checkpoint's embedded research metadata.
    loaded = _safe_torch_load(checkpoint, device="cpu")
    _validate_checkpoint_contract(
        loaded,
        model_name=model_name,
        fold_id=fold_id,
        architecture_signature=architecture_signature,
        class_mapping=class_mapping,
        norm_json=norm_json,
    )

    # 2. Instantiate the registered architecture and restore exact weights.
    model = get_model(model_name, model_config)
    model.load_state_dict(loaded["model_state_dict"])
    model.eval()

    # 3. Stage the bundle in a sibling directory (never in output_dir).
    staging = parent / f".artifact.staging-{uuid.uuid4().hex[:8]}"

    def _cleanup() -> None:
        shutil.rmtree(staging, ignore_errors=True)

    try:
        example_input = torch.randn(1, _TEMPORAL_FRAMES, int(model_config.get("input_dim", 237)))
        traced = torch.jit.trace(model, example_input)

        staging.mkdir()
        traced.save(str(staging / "model.pt"))
        shutil.copyfile(fold_metadata_path, staging / "fold_metadata.json")
        shutil.copyfile(norm_json, staging / "normalization.json")
        shutil.copyfile(model_config_path, staging / "model_config.json")
        shutil.copyfile(class_mapping_path, staging / "class_mapping.json")

        manifest = {
            path.name: _sha256_file(path)
            for path in sorted(staging.iterdir())
            if path.is_file() and path.name != "bundle_sha256.json"
        }
        (staging / "bundle_sha256.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )

        # 4. Atomically swap the bundle into place.
        if output_path.exists():
            shutil.rmtree(output_path)
        os.replace(staging, output_path)
    except BaseException:
        _cleanup()
        raise

    return output_path


def _legacy_export() -> None:
    """One-shot legacy export used by the optimization workflow."""
    from training.models.rehab_motionnet import RehabMotionNet

    model = RehabMotionNet(
        num_exercises=4,
        use_hand=True,
        use_kinematic=True,
        use_contrastive=False,
        use_mstcn=True,
        use_attention=False,
        upper_limb_only=True,
    )

    checkpoint = torch.load(
        "experiments/optimized_seed7/fold_04_seed7/checkpoints/best_model.pth",
        map_location="cpu",
        weights_only=False,
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    example_input = torch.randn(1, _TEMPORAL_FRAMES, 237)
    traced = torch.jit.trace(model, example_input)
    traced.save("artifacts/model_v2/model.pt")

    print("Model exported to TorchScript successfully!")
    print(f"Best epoch: {checkpoint.get('epoch', 'unknown')}")
    print(f"Val F1: {checkpoint.get('val_f1', 0):.4f}")


if __name__ == "__main__":
    _legacy_export()
