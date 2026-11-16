"""Audit artifacts produced by the experimental auto-label pipeline."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--labels',type=Path,required=True); ap.add_argument('--metrics',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); args=ap.parse_args()
    labels=pd.read_csv(args.labels); metrics=json.loads(args.metrics.read_text(encoding='utf-8'))
    labels['source_group']=labels.source_video_path.str.extract(r'\\(ex[123])\\',expand=False).fillna('unknown')
    confirmed=labels[labels.completion_label.isin(['correct','incorrect'])]
    lines=['# Datanew automatic pipeline audit','', '## Scope', '- Labels are `auto_rule_v1`: quartiles of signal range, not expert or clinical ground truth.', '- Metrics are therefore pipeline smoke-test results only.', '', '## Label counts']
    lines += [f'- {r.exercise} / {r.completion_label}: {r.count}' for r in confirmed.groupby(['exercise','completion_label']).size().reset_index(name='count').itertuples()]
    lines += ['', '## Source groups']
    lines += [f'- {r.exercise} / {r.source_group}: {r.count} reviewed rows' for r in confirmed.groupby(['exercise','source_group']).size().reset_index(name='count').itertuples()]
    lines += ['', '## No-leakage smoke test']
    lines += [f'- {r["exercise"]}: F1={r["f1_macro"]:.4f}, accuracy={r["accuracy"]:.4f}' for r in metrics.get('results',[])]
    lines += ['', '## Interpretation', '- The apparent perfect score is expected because auto_rule_v1 defines the target from signal range and related extrema features remain in the input.', '- This is not evidence of correctness recognition.', '- Required next valid evidence: expert-reviewed labels and a predeclared subject-wise split with the labeling rule excluded from features.']
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text('\n'.join(lines),encoding='utf-8'); print(args.output.resolve())
if __name__=='__main__': main()
