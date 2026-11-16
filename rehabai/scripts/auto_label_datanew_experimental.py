"""Generate explicitly experimental, heuristic labels for the review queue.

These labels are not clinical ground truth. Extremes of per-rep signal excursion
are used only to create a research smoke-test set; the middle band remains
uncertain and all rows carry provenance.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--queue',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--report',type=Path,required=True); args=ap.parse_args()
    q=pd.read_csv(args.queue)
    q['signal_range']=pd.to_numeric(q.signal_range,errors='coerce')
    q['completion_label']='uncertain'; q['review_status']='auto_experimental'; q['annotator_id']='auto_rule_v1'; q['reviewed_at']=pd.Timestamp.utcnow().isoformat(); q['notes']='EXPERIMENTAL heuristic: signal-range extreme; not clinical ground truth'
    for ex,g in q.groupby('exercise'):
        lo=float(g.signal_range.quantile(.25)); hi=float(g.signal_range.quantile(.75)); mask=q.exercise.eq(ex)
        q.loc[mask & (q.signal_range<=lo),'completion_label']='incorrect'
        q.loc[mask & (q.signal_range>=hi),'completion_label']='correct'
    args.output.parent.mkdir(parents=True,exist_ok=True); q.to_csv(args.output,index=False,encoding='utf-8-sig')
    counts=q.groupby(['exercise','completion_label']).size().reset_index(name='count')
    lines=['# Experimental automatic labels','', '- Provenance: `auto_rule_v1`', '- Purpose: research smoke test only; labels are not clinically validated.', '- Rule: bottom quartile of signal range = `incorrect`, top quartile = `correct`, middle 50% = `uncertain`.', '', '## Counts']
    lines += [f'- {r.exercise} / {r.completion_label}: {r.count}' for r in counts.itertuples()]
    args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text('\n'.join(lines),encoding='utf-8')
    print(f'rows={len(q)} output={args.output.resolve()}'); print(counts.to_string(index=False))
if __name__=='__main__': main()
