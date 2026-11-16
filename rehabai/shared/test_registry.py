import json
import hashlib
from pathlib import Path

def test_registry_validity():
    registry_path = Path(__file__).parent / "exercise_registry.json"
    assert registry_path.exists(), "exercise_registry.json must exist"
    
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
        
    assert len(registry) == 4, "Registry must contain exactly 4 exercises"
    
    expected_ids = {1, 2, 3, 4}
    actual_ids = {ex["exercise_id"] for ex in registry}
    assert actual_ids == expected_ids, "exercise_id must be exactly {1, 2, 3, 4}"
    
    # Check order
    for i, ex in enumerate(registry):
        assert ex["display_order"] == i + 1, "display_order must be 1, 2, 3, 4"
        
    expected_slugs = ["vai_nang_vat", "khuyu_tay_duoi", "co_tay_nang", "ban_tay_mo"]
    actual_slugs = [ex["slug"] for ex in registry]
    assert actual_slugs == expected_slugs, "Slugs must not change"

def get_registry_sha256():
    registry_path = Path(__file__).parent / "exercise_registry.json"
    with open(registry_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

if __name__ == "__main__":
    print("Running tests...")
    test_registry_validity()
    print("Tests passed!")
    print(f"Registry SHA256: {get_registry_sha256()}")
