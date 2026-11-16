"""Build a research-only runtime bundle from the validated fold-04 ensemble.

The LOSO study selected a different blend weight per fold.  This bundle is
therefore explicitly a demo/research artifact (fold-04, alpha=0.80) and is
never written over ``artifacts/model_v2``.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch

from training.models.ctr_gcn import UpperLimbCTRGCN
OUT = ROOT / "artifacts" / "ensemble_v1_research"
V2 = ROOT / "artifacts" / "model_v2"
CTR_CKPT = ROOT / "experiments" / "ctr_gcn_v1" / "checkpoints" / "fold_04" / "UpperLimbCTRGCN_fold_04_supervised_model.pth"


class EnsembleWrapper(torch.nn.Module):
    def __init__(self, v2: torch.jit.ScriptModule, ctr: torch.jit.ScriptModule, alpha: float):
        super().__init__()
        self.v2 = v2
        self.ctr = ctr
        self.alpha = alpha

    def forward(self, x: torch.Tensor):
        v2_cls, v2_comp = self.v2(x)
        ctr_cls, ctr_comp = self.ctr(x)
        return self.alpha * v2_cls + (1.0 - self.alpha) * ctr_cls, self.alpha * v2_comp + (1.0 - self.alpha) * ctr_comp


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    if not (V2 / "model.pt").is_file() or not CTR_CKPT.is_file():
        raise FileNotFoundError("Required v2/CTR-GCN checkpoints are missing")
    v2 = torch.jit.load(str(V2 / "model.pt"), map_location="cpu").eval()
    ctr = UpperLimbCTRGCN(num_exercises=4, use_hand=True, use_kinematic=True, upper_limb_only=True).eval()
    payload = torch.load(CTR_CKPT, map_location="cpu", weights_only=False)
    ctr.load_state_dict(payload["model_state_dict"], strict=True)
    ctr_script = torch.jit.trace(ctr, torch.zeros(1, 96, 237), check_trace=False, strict=True).eval()
    wrapper = EnsembleWrapper(v2, ctr_script, alpha=0.80).eval()
    traced = torch.jit.trace(wrapper, torch.zeros(1, 96, 237), check_trace=False, strict=True)

    staging = OUT.with_name(OUT.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    traced.save(str(staging / "model.pt"))
    for name in ("exercise_registry.json", "feature_schema.json", "normalization.json", "registry_sha256.txt"):
        shutil.copy2(V2 / name, staging / name)
    # Keep the research evaluation alongside the runtime bundle for auditability.
    shutil.copy2(ROOT / "reports" / "evaluation" / "loso_ensemble_v1.json", staging / "loso_ensemble_v1.json")
    metrics = {
        "evaluation_protocol": "strict subject-wise 10-fold LOSO (research)",
        "exercise": {"macro_f1_mean": 0.3743620476430682, "accuracy_mean": 0.43454170079238535},
        "research_only": True,
        "fold_id": "fold_04",
        "alpha_v2": 0.80,
        "note": "Per-fold LOSO weights differ; this fixed-weight bundle is for demo/research only.",
    }
    (staging / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    config = {
        "model_name": "RehabMotionNet+CTR-GCN Ensemble",
        "version": "1.0-research",
        "model_type": "ensemble",
        "input_dim": 237,
        "temporal_frames": 96,
        "architecture_signature": "ensemble_v1_research",
        "class_mapping": {"0": "Exercise_1", "1": "Exercise_2", "2": "Exercise_3", "3": "Exercise_4"},
        "components": ["rehab_motionnet_upper_limb_v2", "upper_limb_ctr_gcn_v1"],
        "blend": {"alpha_v2": 0.80, "selection": "fold_04 validation", "research_only": True},
        "provenance": {"fold_id": "fold_04", "source_artifact": "model_v2 + CTR-GCN fold_04"},
    }
    (staging / "model_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    card = """# RehabMotionNet + CTR-GCN ensemble (research artifact)\n\nThis fixed-weight fold-04 bundle is for demonstration and research only.\nThe strict LOSO study reported Macro-F1 0.3744 +/- 0.3319 with fold-specific\nvalidation-selected weights. It is not a clinical model and does not replace\na qualified healthcare professional. Production remains `artifacts/model_v2`.\n"""
    (staging / "model_card.md").write_text(card, encoding="utf-8")
    manifest = {p.name: sha256(p) for p in sorted(staging.iterdir()) if p.is_file()}
    (staging / "bundle_sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    if OUT.exists():
        shutil.rmtree(OUT)
    staging.rename(OUT)
    print(f"Created {OUT}")


if __name__ == "__main__":
    main()
