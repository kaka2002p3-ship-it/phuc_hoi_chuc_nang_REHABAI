# Fresh-subject evaluation

Tệp này chỉ là hướng dẫn chuẩn bị. Hãy bổ sung video từ người hoặc buổi quay
không xuất hiện trong train, validation hay test v2; trích xuất bằng extractor
hiện có; sau đó khóa nhãn `correct/incorrect` do chuyên gia duyệt trước khi chạy
inference. Evaluator sẽ từ chối mọi video trùng với split đã biết và không thay
checkpoint hoặc artifact production.

Lệnh chạy sau khi đã chuẩn bị manifest thật:

```powershell
python scripts\evaluate_datanew_fresh_subject.py `
  --manifest data\annotations\fresh_subject_eval_manifest.csv `
  --catalog data\datanew_unlabeled\datanew_exercise_catalog.csv `
  --checkpoint-dir experiments `
  --known-split-dir data\annotations\datanew_expert_split_second_review_v2_seed42 `
  --output reports\evaluation\fresh_subject_predictions.csv
```

Output chỉ dùng cho shadow evaluation. Nếu manifest chứa `completion_label`,
metrics cũng được ghi vào `fresh_subject_predictions.metrics.json`.
