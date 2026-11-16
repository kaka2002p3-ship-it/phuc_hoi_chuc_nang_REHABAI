from scripts.generate_loso import generate_loso_splits


def test_prefers_full_class_coverage_validation(monkeypatch):
    # This unit isolates fold-selection logic; cryptographic eligibility is
    # covered by the provenance and LOSO integration suites.
    monkeypatch.setattr("scripts.generate_loso.filter_or_reject_manifest", lambda records: (records, []))
    records = []
    for subject in ("01", "02"):
        for exercise in (1, 2, 3, 4):
            records.append({"sample_id": f"{subject}-{exercise}", "source_record_id": f"src-{subject}-{exercise}", "subject_id": subject, "exercise_id": exercise, "source_video_sha256": f"{subject}-{exercise}"})
    for subject, exercise in (("03", 1), ("04", 2)):
        records.append({"sample_id": f"{subject}-{exercise}", "source_record_id": f"src-{subject}-{exercise}", "subject_id": subject, "exercise_id": exercise, "source_video_sha256": f"{subject}-{exercise}"})

    folds = generate_loso_splits(records, ["01", "02", "03", "04"])
    for fold in folds.values():
        test_subject = fold["metadata"]["test_subject"]
        val_subject = fold["metadata"]["validation_subjects"][0]
        assert val_subject in {"01", "02"}
        assert val_subject != test_subject
        assert fold["metadata"]["exercise_coverage"]["val"] == [1, 2, 3, 4]
