import hashlib
import json

from backend.knowledge import retriever


def _write_document(tmp_path, monkeypatch, *, status="approved", valid_hash=True):
    approved = tmp_path / "approved"
    metadata = tmp_path / "metadata"
    approved.mkdir(exist_ok=True); metadata.mkdir(exist_ok=True)
    document = approved / "product-help.md"
    document.write_text("Camera cần nhìn rõ bàn tay. Mở lịch sử để xem lại buổi tập.", encoding="utf-8")
    digest = hashlib.sha256(document.read_bytes()).hexdigest()
    (metadata / "product-help.json").write_text(json.dumps({
        "document_id": "product-help",
        "title": "Hướng dẫn camera",
        "source": "verified product behavior",
        "language": "vi",
        "version": "1.0",
        "scope": ["PRODUCT_HELP"],
        "approval_status": status,
        "review_status": status,
        "content_hash": digest if valid_hash else "0" * 64,
    }), encoding="utf-8")
    monkeypatch.setattr(retriever, "APPROVED_DIR", approved)
    monkeypatch.setattr(retriever, "METADATA_DIR", metadata)


def test_retriever_returns_only_matching_approved_chunks(tmp_path, monkeypatch):
    _write_document(tmp_path, monkeypatch)
    items, evidence, version = retriever.retrieve("camera không thấy rõ bàn tay", scopes={"PRODUCT_HELP"})
    assert len(items) == 1
    assert items[0]["evidence_id"] in evidence
    assert items[0]["review_status"] == "approved"
    assert version.startswith("approved-")


def test_retriever_ignores_draft_and_hash_mismatch(tmp_path, monkeypatch):
    _write_document(tmp_path, monkeypatch, status="draft")
    assert retriever.load_approved() == ([], "none-unapproved")
    _write_document(tmp_path, monkeypatch, valid_hash=False)
    assert retriever.load_approved() == ([], "none-unapproved")


def test_retriever_does_not_inject_unrelated_document(tmp_path, monkeypatch):
    _write_document(tmp_path, monkeypatch)
    items, evidence, _ = retriever.retrieve("thời tiết hôm nay", scopes={"PRODUCT_HELP"})
    assert items == [] and evidence == set()
