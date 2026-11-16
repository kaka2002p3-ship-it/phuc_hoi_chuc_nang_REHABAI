"""Fast, read-only acceptance audit for the V3.1 workspace."""
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path

def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("--root", default=Path(__file__).resolve().parents[1]); a=p.parse_args(); r=Path(a.root)
    checks = {}
    checks["registry"] = (r/"shared/exercise_registry.json").is_file()
    checks["upper_limb_loso"] = (r/"reports/evaluation/loso_upper_limb_v2.json").is_file()
    checks["model_v2_artifact"] = all((r/"artifacts/model_v2"/x).is_file() for x in ("model.pt","model_config.json","feature_schema.json","normalization.json","registry_sha256.txt"))
    checks["backend"] = (r/"backend/main.py").is_file()
    checks["frontend"] = (r/"frontend/package.json").is_file()
    checks["compose"] = (r/"deployment/compose.yaml").is_file()
    checks["release"] = (r/"release/compose.yaml").is_file() and (r/"release/model/model.pt").is_file()
    checks["reproducibility_manifest"] = (r/"research/reproducibility_manifest.json").is_file()
    report = {"checks": checks, "pass_count": sum(checks.values()), "total": len(checks), "status": "partial" if not all(checks.values()) else "pass"}
    out=r/"reports/evaluation/v31_compliance_audit.json"; out.write_text(json.dumps(report,indent=2),encoding="utf-8"); print(json.dumps(report,indent=2))

if __name__ == "__main__": main()
