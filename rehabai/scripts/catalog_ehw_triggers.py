"""Catalog EHW videos and trigger annotations; never infer correctness labels."""
from __future__ import annotations
import argparse, hashlib
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); args=ap.parse_args(); root=args.root.resolve(strict=True); rows=[]
    for path in sorted((root/'DataKinects').rglob('*.mp4')):
        rel=path.relative_to(root).as_posix(); parts=path.relative_to(root).parts; subject=parts[1] if len(parts)>1 else 'unknown'; code=path.parent.name.replace('Prova_','')
        rows.append({'sample_id':'EHW_'+hashlib.sha1(rel.encode()).hexdigest()[:12],'file':str(path),'relative_path':rel,'subject_id':subject,'protocol_code':code,'exercise':'UNKNOWN','completion_label':'unknown','boundary_label_status':'unlinked_pending'})
    out=args.output; out.parent.mkdir(parents=True,exist_ok=True); pd.DataFrame(rows).to_csv(out,index=False,encoding='utf-8-sig'); print(f'video_catalog={out.resolve()} rows={len(rows)}'); print(pd.Series([r['subject_id'] for r in rows]).value_counts().to_string())
if __name__=='__main__': main()
