"""Strictly evaluate upper-limb v2 and write the comparative final report."""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/stage3_upper_limb"
EXP = ROOT / "experiments/upper_limb_v1"
REPORTS = ROOT / "reports/evaluation"
MAPPING = {"0":"Exercise_1","1":"Exercise_2","2":"Exercise_3","3":"Exercise_4"}

def jobs(checkpoint_root: Path, upper_v2: bool):
    result=[]
    for i in range(1,11):
        fold=f"fold_{i:02d}"; fd=DATA/"loso"/fold
        result.append({
            "fold_id":fold,"model_name":"RehabMotionNet",
            "data_dir":str(DATA/"processed/keypoints"),
            "source_dir":str(ROOT.parent/"RehabAI_Datasets_FULL_VERIFIED/01_Upper_Limb_Stroke"),
            "split_manifest":str(fd/"test_manifest.csv"),
            "normalization_json":str(fd/"normalization.json"),
            "checkpoint_path":str(checkpoint_root/fold/f"RehabMotionNet_{fold}_supervised_model.pth"),
            "fold_metadata_path":str(fd/"metadata.json"),
            "expected_model_config":{
                "use_hand":True,"use_kinematic":True,"use_contrastive":True,
                "use_mstcn":True,"use_attention":True,"upper_limb_only":upper_v2,
            } if upper_v2 else {
                "use_hand":True,"use_kinematic":True,"use_contrastive":True,
                "use_mstcn":True,"use_attention":True,
            },
            "expected_architecture_signature":"rehab_motionnet_upper_limb_v2" if upper_v2 else "rehab_motionnet_v1",
            "expected_class_mapping":MAPPING,
        })
    return result

def evaluate(name: str, js):
    config=EXP/f"{name}_eval_config.json"; output=REPORTS/f"{name}.json"
    config.write_text(json.dumps({"jobs":js,"output_file":str(output)},indent=2),encoding="utf-8")
    subprocess.run([sys.executable,str(ROOT/"scripts/evaluate.py"),str(config)],cwd=ROOT,check=True)
    return json.loads(output.read_text(encoding="utf-8"))

def means(rows):
    keys=("f1_macro","accuracy","completion_f1_macro","completion_accuracy")
    return {k:sum(float(x[k]) for x in rows)/len(rows) for k in keys}

def main():
    REPORTS.mkdir(parents=True,exist_ok=True)
    v2=evaluate("loso_upper_limb_v2",jobs(EXP/"training/checkpoints",True))
    prior_v1_path=REPORTS/"loso_upper_limb_rehabmotionnet.json"
    v1=json.loads(prior_v1_path.read_text(encoding="utf-8")) if prior_v1_path.exists() else []
    m2=means(v2)
    m1={"f1_macro":sum(x["f1_macro"] for x in v1)/len(v1),"accuracy":sum(x["accuracy"] for x in v1)/len(v1),"completion_f1_macro":float("nan"),"completion_accuracy":float("nan")} if v1 else {k:float("nan") for k in ("f1_macro","accuracy","completion_f1_macro","completion_accuracy")}
    old_path=REPORTS/"loso_rehabmotionnet.json"
    old=json.loads(old_path.read_text(encoding="utf-8")) if old_path.exists() else []
    old_f1=sum(x["f1_macro"] for x in old)/len(old) if old else float("nan")
    winner="v2" if m2["f1_macro"] > m1["f1_macro"] else "v1"
    lines=["# Upper-limb RehabMotionNet Final Report","",
           "## Outcome","",
           f"Selected model: **{winner}** based on held-out LOSO exercise Macro-F1.","",
           "| Experiment | Samples | Exercise Macro-F1 | Exercise Accuracy | Completion Macro-F1 | Completion Accuracy |",
           "|---|---:|---:|---:|---:|---:|",
           f"| Original full-pose | 202 | {old_f1:.4f} | - | - | - |",
           f"| Upper-limb v1 | 387 | {m1['f1_macro']:.4f} | {m1['accuracy']:.4f} | {m1['completion_f1_macro']:.4f} | {m1['completion_accuracy']:.4f} |",
           f"| Upper-limb v2 (6 joints + balanced loss) | 387 | {m2['f1_macro']:.4f} | {m2['accuracy']:.4f} | {m2['completion_f1_macro']:.4f} | {m2['completion_accuracy']:.4f} |","",
           "## Per-fold v2","","| Fold | N | Exercise F1 | Accuracy | Completion F1 | Completion Accuracy |","|---|---:|---:|---:|---:|---:|"]
    for x in v2:
        lines.append(f"| {x['fold_id']} | {x['sample_count']} | {x['f1_macro']:.4f} | {x['accuracy']:.4f} | {x['completion_f1_macro']:.4f} | {x['completion_accuracy']:.4f} |")
    lines += ["","## Scientific limitation","",
              "Subjects 07–10 contain restricted exercise coverage. Their fold Macro-F1 includes all four canonical classes and therefore correctly penalizes missing-class generalization. No test subject was used for training, normalization, checkpoint selection, or pseudo-labeling."]
    (REPORTS/"UPPER_LIMB_V2_FINAL_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"status":"complete","selected":winner,"v1":m1,"v2":m2},indent=2))
if __name__=="__main__": main()
