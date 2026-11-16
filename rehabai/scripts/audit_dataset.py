import os
import json
import csv
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
INDEXES_DIR = DATA_DIR / "indexes"
TABLES_DIR = PROJECT_ROOT / "research" / "tables"
REGISTRY_PATH = PROJECT_ROOT / "shared" / "exercise_registry.json"

DATASET_ROOT = PROJECT_ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED"
UPPER_LIMB_DIR = DATASET_ROOT / "01_Upper_Limb_Stroke"
REHAB24_DIR = DATASET_ROOT / "02_REHAB24-6"
MOBIPHYSIO_DIR = DATASET_ROOT / "03_MobiPhysio"

def load_registry():
    with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def audit_upper_limb(registry):
    print("Auditing Upper Limb Stroke...")
    dataset_dir = UPPER_LIMB_DIR / "dataset" / "An upper limb stroke rehabilitation exercise video" / "Exercise"
    if not dataset_dir.exists():
        print(f"Directory not found: {dataset_dir}")
        return []

    records = []
    folder_mapping = {
        "1_Lifting an Object": 1,
        "2_Extending the Elbow": 2,
        "3_Lifting the Wrist": 3,
        "4_Opening the Hand": 4
    }

    ex_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    
    for root, _, files in os.walk(dataset_dir):
        for file in files:
            if not file.lower().endswith('.mp4'):
                continue
            
            abs_path = Path(root) / file
            rel_path = abs_path.relative_to(UPPER_LIMB_DIR)
            
            parts = rel_path.parts
            exercise_folder = parts[3]
            if exercise_folder not in folder_mapping:
                continue
            
            exercise_id = folder_mapping[exercise_folder]
            completion_label = parts[4].lower() 
            source_split = parts[5].lower() 
            
            subject_id = file.split('_')[0]
            
            ex_info = next((e for e in registry if e["exercise_id"] == exercise_id), None)
            
            records.append({
                "dataset": "Upper_Limb_Stroke",
                "file": str(abs_path),
                "relative_path": str(rel_path),
                "subject_id": subject_id,
                "exercise_id": exercise_id,
                "region_vi": ex_info["region_vi"] if ex_info else "",
                "exercise_vi": ex_info["exercise_vi"] if ex_info else "",
                "slug": ex_info["slug"] if ex_info else "",
                "completion_label": completion_label,
                "source_split": source_split
            })
            ex_counts[exercise_id] += 1
            
    print(f"Upper Limb Total: {len(records)}")
    print(f"Counts per exercise: {ex_counts}")
    return records

def audit_rehab24():
    print("Auditing REHAB24-6...")
    csv_path = REHAB24_DIR / "Segmentation.csv"
    records = []
    if not csv_path.exists():
        print(f"Segmentation.csv not found: {csv_path}")
        return records
        
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["dataset"] = "REHAB24-6"
            records.append(row)
            
    print(f"REHAB24-6 Total: {len(records)}")
    return records

def audit_mobiphysio():
    print("Auditing MobiPhysio...")
    json_path = MOBIPHYSIO_DIR / "MobiPhysio_metadata.json"
    records = []
    if not json_path.exists():
        print(f"Metadata not found: {json_path}")
        return records
        
    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    item["dataset"] = "MobiPhysio"
                    records.append(item)
            elif isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict):
                        v["video_id"] = k
                        v["dataset"] = "MobiPhysio"
                        records.append(v)
        except Exception as e:
            print(f"Error parsing MobiPhysio metadata: {e}")
            
    print(f"MobiPhysio Total: {len(records)}")
    return records

def save_csv(records, output_path):
    if not records:
        return
    # Collect all possible keys
    keys = []
    for r in records:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
                
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(records)

def main():
    registry = load_registry()
    
    INDEXES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    
    ul_records = audit_upper_limb(registry)
    save_csv(ul_records, INDEXES_DIR / "upper_limb_master.csv")
    
    r24_records = audit_rehab24()
    save_csv(r24_records, INDEXES_DIR / "rehab24_master.csv")
    
    mobi_records = audit_mobiphysio()
    save_csv(mobi_records, INDEXES_DIR / "mobiphysio_master.csv")
    
    # Assert conditions for Upper Limb
    if len(ul_records) != 491:
        print(f"[FAIL] Expected 491 Upper Limb videos, got {len(ul_records)}")
    
    ex_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for r in ul_records:
        ex_counts[r["exercise_id"]] += 1
        
    if ex_counts[1] != 123 or ex_counts[2] != 127 or ex_counts[3] != 121 or ex_counts[4] != 120:
        print(f"[FAIL] Upper Limb classes count mismatch. Got: {ex_counts}")
    else:
        print("[PASS] Upper Limb counts are absolutely correct: 491 total, [123, 127, 121, 120].")
    
    # Dataset statistics
    stats = [
        {"Dataset": "Upper Limb Stroke", "Videos": len(ul_records)},
        {"Dataset": "REHAB24-6", "Segments": len(r24_records)},
        {"Dataset": "MobiPhysio", "Videos": len(mobi_records)}
    ]
    save_csv(stats, TABLES_DIR / "dataset_statistics.csv")
    
    # General audit CSV
    all_audit = []
    for r in ul_records:
        all_audit.append({"dataset": r.get("dataset"), "file": r.get("file"), "label": r.get("completion_label")})
    for r in r24_records:
        all_audit.append({"dataset": r.get("dataset"), "file": r.get("Video", ""), "label": r.get("Correctness", "")})
    for r in mobi_records:
        all_audit.append({"dataset": r.get("dataset"), "file": r.get("video_id", ""), "label": r.get("score", "")})
        
    save_csv(all_audit, INDEXES_DIR / "dataset_audit.csv")
    print(f"Saved indexes to: {INDEXES_DIR}")

if __name__ == "__main__":
    main()
