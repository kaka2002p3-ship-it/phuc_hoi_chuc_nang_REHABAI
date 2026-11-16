import json
from pathlib import Path

from scripts.build_local_ai_corpus import OUT, build
from scripts.validate_local_ai_corpus import main as validate


def test_local_ai_corpus_build_is_fail_closed():
    manifest = build()
    assert manifest["rag_ready"] is True
    assert manifest["sft_ready"] is False
    assert manifest["eval_ready"] is False
    assert manifest["human_review_pending"] > 0
    assert validate() == 0
    for path in (OUT / "processed" / "conversations").glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            assert json.loads(line)["review_status"] != "APPROVED"


def test_only_reviewed_product_knowledge_is_in_approved_rag():
    build()
    rows = []
    for path in (OUT / "approved" / "rag").glob("*.jsonl"):
        rows += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert rows
    assert all(row["review_status"] == "APPROVED" and row["source_id"] for row in rows)
