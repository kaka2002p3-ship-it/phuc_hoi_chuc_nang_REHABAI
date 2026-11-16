"""Read-only structural audit for the public stroke reaching workbook source.

This deliberately does not infer RehabAI exercise or completion labels. It only
checks whether the workbooks contain sufficiently regular numeric trajectories
for a separately predeclared representation-learning adapter.
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "main": "http://purl.oclc.org/ooxml/spreadsheetml/main",
    "rel": "http://purl.oclc.org/ooxml/officeDocument/relationships",
}
REL_NS = "http://purl.oclc.org/ooxml/officeDocument/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def inspect_workbook(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relation_map = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in rels
            if item.attrib.get("Type", "").endswith("/worksheet")
        }
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root:
                shared.append("".join(node.text or "" for node in item.iter() if _local(node.tag) == "t"))
        sheets = []
        for sheet in workbook.iter():
            if _local(sheet.tag) != "sheet":
                continue
            name = sheet.attrib.get("name", "")
            rid = sheet.attrib.get(f"{{{REL_NS}}}id") or sheet.attrib.get("r:id", "")
            target = relation_map.get(rid)
            if not target:
                continue
            target = target.lstrip("/")
            sheet_path = Path("xl") / target if not target.startswith("xl/") else Path(target)
            root = ET.fromstring(archive.read(sheet_path.as_posix()))
            rows = [node for node in root.iter() if _local(node.tag) == "row"]
            max_col = 0
            first_values = []
            for row in rows[:3]:
                values = []
                for cell in row:
                    if _local(cell.tag) != "c":
                        continue
                    ref = cell.attrib.get("r", "")
                    letters = re.sub(r"[^A-Z]", "", ref)
                    if letters:
                        max_col = max(max_col, sum((ord(ch) - 64) * 26**i for i, ch in enumerate(reversed(letters))))
                    value = ""
                    v = next((node for node in cell if _local(node.tag) == "v"), None)
                    if v is not None and v.text is not None:
                        value = v.text
                        if cell.attrib.get("t") == "s" and value.isdigit() and int(value) < len(shared):
                            value = shared[int(value)]
                    values.append(value)
                first_values.append(values[:20])
            sheets.append({"name": name, "row_count": len(rows), "max_column": max_col, "first_rows": first_values})
        return {"file": path.name, "bytes": path.stat().st_size, "sheets": sheets}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    files = sorted(args.root.glob("S*.xlsx"))
    records = [inspect_workbook(path) for path in files]
    subjects = sorted({match.group(1) for path in files if (match := re.match(r"S(\d+)_", path.name))})
    trial_files = [record for record in records if any(sheet["row_count"] >= 20 for sheet in record["sheets"])]
    result = {
        "audit_status": "PASS_STRUCTURAL_ONLY" if records else "FAIL_NO_WORKBOOKS",
        "workbook_count": len(records),
        "subject_count": len(subjects),
        "subjects": subjects,
        "workbooks_with_nontrivial_rows": len(trial_files),
        "workbooks": records,
        "product_label_mapping": False,
        "product_training_admitted": False,
        "training_recommendation": "separate_kinematic_ssl_adapter_review_required",
        "limitations": [
            "XLSX trajectories are not MediaPipe 33-joint skeletons.",
            "Source movement names cannot be mapped to the four product exercises.",
            "A trajectory-only adapter must pass a predeclared strict LOSO gate before use.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("audit_status", "workbook_count", "subject_count", "workbooks_with_nontrivial_rows", "training_recommendation")}, indent=2))


if __name__ == "__main__":
    main()
