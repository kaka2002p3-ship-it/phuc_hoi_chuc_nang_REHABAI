"""Create a safe, empty rep-level annotation manifest from verified target videos."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

COLUMNS = ["schema_version", "video_id", "subject_id", "exercise_id", "exercise_name",
           "source_video_path", "rep_id", "start_frame", "end_frame", "completion_label",
           "annotator_id", "review_status", "notes"]

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--index", default="data/indexes/upper_limb_master.csv"); parser.add_argument("--output", default="data/annotations/rep_annotations.csv"); args=parser.parse_args()
    source=pd.read_csv(args.index,dtype={"subject_id":str})
    source=source[source.exercise_id.isin([2,4])].copy()
    names={2:"ELBOW_EXTENSION",4:"HAND_OPENING"}
    rows=[]
    for _,row in source.iterrows():
        rows.append({"schema_version":"1.0","video_id":Path(str(row["file"])).stem,
                     "subject_id":row["subject_id"],"exercise_id":int(row["exercise_id"]),
                     "exercise_name":names[int(row["exercise_id"])],"source_video_path":row["file"],
                     "rep_id":"","start_frame":"","end_frame":"","completion_label":"",
                     "annotator_id":"","review_status":"pending","notes":""})
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows,columns=COLUMNS).to_csv(output,index=False,encoding="utf-8-sig")
    print(f"Created {output} with {len(rows)} pending target videos; no labels were fabricated.")
if __name__=="__main__": main()
