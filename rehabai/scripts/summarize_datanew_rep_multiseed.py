"""Summarize strict experimental rep baselines across seeds."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--metrics',type=Path,nargs='+',required=True); ap.add_argument('--output',type=Path,required=True); args=ap.parse_args()
    rows=[]
    for p in args.metrics:
        d=json.loads(p.read_text(encoding='utf-8'))
        for r in d['results']: rows.append({'seed':d['seed'],**{k:r[k] for k in ['exercise','f1_macro','accuracy','test_rows','test_videos']}})
    lines=['# Datanew strict multi-seed smoke test','', '- Labels: `auto_rule_v1` heuristic, not clinical ground truth.', '- Split: grouped by video ID; strict features contain timing only.', '', '## Per-seed results','', '| Seed | Exercise | Macro-F1 | Accuracy | Test reps | Test videos |','|---:|---|---:|---:|---:|---:|']
    lines += [f"| {r['seed']} | {r['exercise']} | {r['f1_macro']:.4f} | {r['accuracy']:.4f} | {r['test_rows']} | {r['test_videos']} |" for r in rows]
    lines += ['', '## Mean ± standard deviation','']
    for ex in sorted(set(r['exercise'] for r in rows)):
        group=[r for r in rows if r['exercise']==ex]; f=np.array([r['f1_macro'] for r in group]); a=np.array([r['accuracy'] for r in group])
        lines.append(f'- {ex}: Macro-F1 `{f.mean():.4f} ± {f.std(ddof=1):.4f}`, accuracy `{a.mean():.4f} ± {a.std(ddof=1):.4f}`.')
    lines += ['', '## Decision', '', '- Research pipeline: PASS.', '- Stable clinical correctness evidence: FAIL.', '- Production promotion: FAIL.', '- Reason: labels are generated from a heuristic and results vary materially by held-out videos/seeds.']
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text('\n'.join(lines),encoding='utf-8'); print(args.output.resolve())
if __name__=='__main__': main()
