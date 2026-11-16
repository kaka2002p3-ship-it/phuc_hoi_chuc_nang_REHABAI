"""Build an isolated upper-limb quality log from Stage 3 raw extractions.

This experiment accepts samples rejected for full-body pose when the six
upper-limb joints (shoulders, elbows, wrists) are visible in >=30% of frames.
The original quality log is never modified.
"""
from __future__ import annotations
import argparse, csv
from pathlib import Path
import numpy as np

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, default=Path('data/stage3_real/indexes/extraction_quality.csv'))
    ap.add_argument('--output', type=Path, default=Path('data/stage3_upper_limb/indexes/extraction_quality.csv'))
    ap.add_argument('--interim-dir', type=Path, default=Path('data/stage3_real/interim/keypoints'))
    args = ap.parse_args()
    rows = list(csv.DictReader(args.input.open(encoding='utf-8')))
    out=[]
    for row in rows:
        p=args.interim_dir / row['output']
        with np.load(p, allow_pickle=False) as z:
            pose=np.asarray(z['pose_landmarks'])
            arm=~np.all(pose[:, [11,12,13,14,15,16], :3] == 0, axis=2)
            rate=float(arm.mean())
        if row['status']=='success' or rate >= 0.30:
            r=dict(row)
            r['status']='success'
            r['extractor_version']=str(row['extractor_version'])+'; upper-limb-gate-v1'
            r['upper_limb_missing_rate']=str(1.0-rate)
            out.append(r)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields=list(out[0])
    if 'upper_limb_missing_rate' not in fields: fields.append('upper_limb_missing_rate')
    with args.output.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
    print(f'upper_limb_candidates={len(out)} from total={len(rows)}')
    return 0
if __name__=='__main__': raise SystemExit(main())
