"""Build a provenance-preserving catalog for local datanew exercise videos.

The folder name is retained as the source label. Elbow flexion is deliberately
not mapped to ELBOW_EXTENSION, and completion labels remain unknown.
"""
from __future__ import annotations
import argparse, hashlib
from pathlib import Path
import pandas as pd

def digest(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--manifest',type=Path,nargs='*',default=[]); args=ap.parse_args(); root=args.source_root.resolve(strict=True); rows=[]
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in {'.mp4','.mov'}: continue
        rel=path.relative_to(root).as_posix(); parts=path.relative_to(root).parts
        if not parts or parts[0] not in {'ex1','ex2','ex3'}: continue
        group=parts[0]; source_label=parts[1] if len(parts)>1 else 'unknown'
        if source_label.casefold()=='mở bàn tay': exercise='HAND_OPENING'
        elif source_label.casefold() in {'gập khuỷu tay','gập khuyu tay'}: exercise='ELBOW_FLEXION'
        else: exercise='UNKNOWN'
        rows.append({'sample_id':'DN_'+hashlib.sha1(rel.encode()).hexdigest()[:12],'dataset':'datanew_local','file':str(path),'relative_path':rel,'subject_id':group,'source_exercise_label':source_label,'exercise':exercise,'completion_label':'unknown','label_status':'pending','source_sha256':digest(path)})
    df=pd.DataFrame(rows)
    if args.manifest:
        mf=pd.concat([pd.read_csv(path) for path in args.manifest],ignore_index=True)
        mf['_key']=mf['file'].map(lambda x: str(Path(x).resolve()).casefold())
        df['_key']=df['file'].map(lambda x: str(Path(x).resolve()).casefold())
        keep=[c for c in ['status','pose_missing_rate','output','sampled_frames','frames'] if c in mf.columns]
        df=df.merge(mf[['_key']+keep].drop_duplicates('_key'),on='_key',how='left').drop(columns=['_key'])
    out=args.output; out.parent.mkdir(parents=True,exist_ok=True); df.to_csv(out,index=False,encoding='utf-8-sig'); print(f'catalog={out.resolve()} rows={len(df)}'); print(df.groupby(['exercise'] + (['status'] if 'status' in df else []),dropna=False).size().to_string())
if __name__=='__main__': main()
