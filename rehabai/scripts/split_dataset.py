import os
import json
import yaml
import argparse
from pathlib import Path
import pandas as pd

def get_subject_id(file_path):
    """
    Extract subject ID from Upper Limb Stroke dataset file path.
    Example: 07_01_01_04.mp4 -> 07
    """
    basename = os.path.basename(file_path)
    # Usually the first 2 digits are subject id
    parts = basename.split('_')
    if len(parts) >= 1:
        return parts[0]
    return "unknown"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index_csv", type=str, default="data/indexes/extraction_quality.csv")
    parser.add_argument("--registry", type=str, default="shared/exercise_registry.json")
    parser.add_argument("--out_csv", type=str, default="data/indexes/splits/split_manifest.csv")
    parser.add_argument("--out_yaml", type=str, default="training/configs/split.yaml")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Create dirs
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_yaml).parent.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(args.index_csv):
        print(f"Index CSV not found: {args.index_csv}")
        return

    # Load registry
    registry_map = {}
    if os.path.exists(args.registry):
        with open(args.registry, "r", encoding="utf-8") as f:
            registry = json.load(f)
            for ex in registry:
                registry_map[ex["slug"]] = ex["exercise_id"]

    df = pd.read_csv(args.index_csv)
    # Use all files that have a valid output npz
    df = df.dropna(subset=['output'])

    # Parse subject_id
    df['subject_id'] = df['file'].apply(get_subject_id)
    
    # Parse exercise label from path: .../Exercise/1_Lifting an Object/...
    def parse_label(path):
        parts = str(path).replace('\\', '/').split('/')
        try:
            ex_idx = parts.index('Exercise')
            return parts[ex_idx + 1]
        except ValueError:
            return "unknown"
            
    df['label'] = df['file'].apply(parse_label)
    
    # Parse completion status: 1 = Complete, 0 = Incomplete
    def parse_completion(path):
        path_str = str(path).replace('\\', '/').lower()
        if '/complete/' in path_str:
            return 1
        elif '/incomplete/' in path_str:
            return 0
        return -1
        
    df['completion'] = df['file'].apply(parse_completion)
    
    df['dataset'] = "Upper_Limb_Stroke"
    df['sample_id'] = df['output']

    # We map exercise_id if possible
    def map_ex_id(label):
        if "1_Lifting" in label: return 1
        if "2_Extending" in label: return 2
        if "3_Lifting" in label: return 3
        if "4_Opening" in label: return 4
        return -1
        
    df['exercise_id'] = df['label'].apply(map_ex_id)

    # Hardcode LOSO Split as requested in Phase 4.6
    train_dfs = []
    val_dfs = []
    test_dfs = []
    
    for idx, row in df.iterrows():
        sub_id = int(row['subject_id'])
        if sub_id in [9, 10]:
            test_dfs.append(row)
        elif sub_id in [7, 8]:
            val_dfs.append(row)
        else:
            train_dfs.append(row)
            
    train_df = pd.DataFrame(train_dfs)
    if not train_df.empty: train_df['split'] = 'train'
    val_df = pd.DataFrame(val_dfs)
    if not val_df.empty: val_df['split'] = 'val'
    test_df = pd.DataFrame(test_dfs)
    if not test_df.empty: test_df['split'] = 'test'
    
    # Combine
    final_df = pd.concat([df for df in [train_df, val_df, test_df] if not df.empty], ignore_index=True)
    
    # Select final columns
    manifest = final_df[['sample_id', 'subject_id', 'dataset', 'split', 'exercise_id', 'label', 'completion']]
    
    manifest.to_csv(args.out_csv, index=False)
    print(f"Saved split manifest to {args.out_csv}")
    
    # Verify no intersection
    train_subs = set(train_df['subject_id'].unique())
    val_subs = set(val_df['subject_id'].unique())
    test_subs = set(test_df['subject_id'].unique()) if not test_df.empty else set()
    
    assert train_subs.isdisjoint(val_subs), "Data leakage: Train and Val subjects intersect!"
    assert train_subs.isdisjoint(test_subs), "Data leakage: Train and Test subjects intersect!"
    assert val_subs.isdisjoint(test_subs), "Data leakage: Val and Test subjects intersect!"
    
    print("\nData Leakage Check Passed: No intersection of subjects between splits.")
    
    # Create YAML config
    config = {
        "split_strategy": "subject_wise",
        "ratios": {"train": 0.7, "val": 0.15, "test": 0.15},
        "seed": args.seed,
        "train_subjects": list(train_subs),
        "val_subjects": list(val_subs),
        "test_subjects": list(test_subs),
        "total_samples": len(final_df)
    }
    
    with open(args.out_yaml, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)
        
    print(f"Saved split config to {args.out_yaml}")

if __name__ == "__main__":
    main()
