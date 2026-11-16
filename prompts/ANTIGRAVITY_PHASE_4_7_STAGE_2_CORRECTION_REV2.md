# PHASE 4.7 — STAGE 2 CORRECTION REV2

## 1. Mục tiêu

Hoàn tất Stage 2 Pipeline Hardening bằng cách sửa các lỗi còn tồn tại sau lần Correction thứ nhất. Mục tiêu là làm cho provenance, True LOSO, normalization, Dataset, checkpoint và evaluation thực sự fail-closed, có liên kết định danh có thể kiểm chứng và được bảo vệ bằng unit test có ý nghĩa.

Kết quả `PASS` trong `PHASE_4_7_STAGE_2_CORRECTION_REPORT.md` chưa được reviewer chấp nhận. Không được bắt đầu Stage 3 cho đến khi toàn bộ tiêu chí trong tài liệu này đạt yêu cầu.

## 2. Phạm vi và giới hạn bắt buộc

1. Đọc toàn bộ file này trước khi sửa.
2. Đọc các tài liệu và mã nguồn sau:
   - `ANTIGRAVITY_PHASE_4_7_STAGE_2_PIPELINE_HARDENING.md`
   - `ANTIGRAVITY_PHASE_4_7_STAGE_2_CORRECTION.md`
   - `PHASE_4_7_STAGE_2_CORRECTION_REPORT.md` nếu có trong dự án
   - `implementation_plan.md` nếu có trong dự án
   - `rehabai/shared/provenance.py`
   - `rehabai/scripts/generate_loso.py`
   - `rehabai/training/normalization.py`
   - `rehabai/training/datasets/rehab_dataset.py`
   - `rehabai/training/datasets/ssl_dataset.py`
   - `rehabai/training/checkpoint_utils.py`
   - `rehabai/training/train.py`
   - `rehabai/training/pretrain.py`
   - `rehabai/training/baseline_trainer.py`
   - `rehabai/training/proposed_trainer.py`
   - `rehabai/scripts/evaluate_baselines.py`
   - toàn bộ test Stage 2 hiện có.
3. Chỉ sửa mã hạ tầng và test liên quan Stage 2.
4. Không chạy extraction, preprocessing, pretraining, supervised training, evaluation hoặc inference thật.
5. Không mở/xử lý 491 video thật trong test.
6. Không xóa, đổi tên hoặc ghi đè video, feature, checkpoint, metric hay báo cáo nghiên cứu hiện có.
7. Test chỉ được ghi vào `tmp_path`, `tempfile` hoặc thư mục tạm tương đương.
8. Không tạo test artifact trong `data/`, `results/`, `training/checkpoints/`, `training/runs/`, `data/models/weights/` hoặc thư mục kết quả thật.
9. Không sửa test theo hướng làm giảm tiêu chí. Không được dùng test rỗng, `pass`, unconditional skip hoặc mock chính hàm đang cần kiểm chứng.
10. Không tự động chuyển sang Stage 3 sau khi hoàn thành.

## 3. Các lỗi reviewer đã xác nhận

### Lỗi 1 — Evaluation chưa fail-closed

Trong `rehabai/scripts/evaluate_baselines.py`, vòng lặp model vẫn bắt `Exception`, đưa lỗi vào `results`, ghi `metrics.json` và kết thúc bình thường. Thiếu checkpoint hoặc evaluation failure phải làm command thất bại với exit code khác 0. Không được tạo một file có thể bị hiểu là kết quả evaluation thành công.

### Lỗi 2 — Artifact hash chưa được đối chiếu

`fit_fold_normalization()` đọc `canonical_provenance_manifest_hash` nhưng không chứng minh hash đó khớp canonical manifest đầu vào. `RehabDataset` và `SSLRehabDataset` mới chỉ kiểm tra `fold_id`, chưa xác minh provenance hash và train-manifest hash gắn với normalization.

### Lỗi 3 — Eligibility tin dữ liệu tự khai báo trong CSV

`check_eligibility()` có thể tin `source_video_exists=True`, `processed_exists=True` và một chuỗi 64 ký tự bất kỳ mà không kiểm tra đường dẫn và nội dung file. Một manifest bị sửa có thể làm file không tồn tại hoặc hash giả trở nên eligible.

### Lỗi 4 — Canonical provenance hash chưa ổn định

`canonical_provenance_hash()` chưa loại trường `provenance_hash` của chính record. Hash gọi lần hai có thể khác lần đầu. Hash hiện có thể phụ thuộc đường dẫn tuyệt đối, làm kết quả khác giữa các máy dù dữ liệu và relative dataset identity giống nhau.

### Lỗi 5 — LOSO vẫn dùng `assert`

Các invariants phân tách subject/source trong `generate_loso.py` vẫn dùng `assert`. Python có thể tắt assert bằng optimization flag. Mọi ràng buộc ảnh hưởng tính đúng đắn nghiên cứu phải dùng explicit validation và raise exception.

### Lỗi 6 — `training/train.py` không tương thích Dataset mới

`RehabDataset` hiện bắt buộc `fold_id`, nhưng các lời gọi trong `training/train.py` chưa truyền tham số này. Entry point này sẽ lỗi trước khi huấn luyện.

### Lỗi 7 — Checkpoint contract chưa đầy đủ và bị bypass

`load_checkpoint()` chỉ đối chiếu fold và provenance hash. Nó chưa kiểm tra model ID, protocol version, train-manifest hash, class mapping và model configuration. `proposed_trainer.py` vẫn load pretrained encoder bằng `torch.load()` trực tiếp thay vì contract an toàn.

### Lỗi 8 — Test coverage không đủ

`test_check_eligibility_tampered_hash()` hiện chỉ có `pass`. Không có test correction đầy đủ cho LOSO, normalization leakage/hash binding, evaluator fail-closed, source group isolation, trainer entry point compatibility và checkpoint metadata mismatch.

## 4. Công việc bắt buộc

### A. Làm canonical hashing ổn định và portable

1. Định nghĩa rõ danh sách trường canonical được đưa vào hash. Dùng allowlist thay vì lấy mọi trường trừ vài trường.
2. Loại khỏi payload hash tối thiểu:
   - `provenance_hash`
   - `exclusion_reasons`
   - timestamp/runtime-only fields
   - đường dẫn tuyệt đối phụ thuộc máy.
3. Dùng canonical relative path hoặc stable dataset-relative identity cho source và processed feature.
4. Chuẩn hóa string, boolean, số, `None` và `NaN` trước khi serialize.
5. Serialize deterministic bằng JSON với sorted keys và separators cố định.
6. Hàm hash phải idempotent:
   - `hash(record) == hash(record)`
   - thêm chính giá trị `provenance_hash` vào record không được làm hash thay đổi
   - thay đổi một trường canonical phải làm hash thay đổi.
7. Hash toàn manifest phải không phụ thuộc thứ tự record hoặc thứ tự dictionary key.
8. Ghi schema/protocol version trong canonical payload để tránh nhập nhằng giữa các phiên bản.

### B. Làm eligibility chống giả mạo và fail-closed

Thiết kế hai lớp rõ ràng:

1. **Schema/logical validation**: kiểm tra status, subject, exercise, label, split/fold fields và checksum format.
2. **Physical integrity validation**: kiểm tra file thật tồn tại, tính SHA256 thực tế và so với manifest.

Yêu cầu:

- Không được coi boolean `source_video_exists` hoặc `processed_exists` trong CSV là bằng chứng cuối cùng.
- Khi chế độ research/training được gọi, phải kiểm tra `Path.is_file()` trên source video và processed feature.
- Phải tính lại SHA256 của processed feature và so khớp manifest.
- Khi canonical contract yêu cầu source checksum, phải tính và so khớp source video checksum.
- Chuỗi checksum phải đúng 64 ký tự hexadecimal; chỉ kiểm tra độ dài là không đủ.
- `data_status` phải là `REAL_VERIFIED`.
- `extraction_status` phải là `success`.
- `quality_gate_passed` phải được parse nghiêm ngặt. Các giá trị `NaN`, rỗng, `"false"`, `"0"` không được trở thành truthy do cách ép kiểu Python.
- `exclusion_reasons` phải rỗng đối với eligible record.
- Subject phải thuộc expected subject set được cấu hình, không chỉ cần khác `unknown`.
- Exercise và completion label phải thuộc class mapping được cấu hình.
- Không được cho caller tự nâng record lên `REAL_VERIFIED` mà không có verification evidence/authority được định nghĩa rõ.
- Tách API nếu cần để unit test logical validation mà không đọc dữ liệu lớn, nhưng production entry point phải dùng physical integrity validation.

### C. Liên kết provenance → fold → normalization → Dataset → checkpoint

Tạo các helper dùng chung cho artifact identity. Mỗi bước phải xác minh đầu vào trước khi tạo đầu ra.

#### Fold metadata

Phải chứa:

- protocol/schema version
- `fold_id`
- canonical provenance manifest hash
- hashes của train/val/test manifest sau khi serialize canonical
- test subject, validation subjects, train subjects
- sample counts
- deterministic split rule/seed.

#### Normalization artifact

Trước khi fit:

- Tính lại hash train manifest và so với fold metadata.
- Xác minh canonical provenance hash được cung cấp khớp fold metadata.
- Xác minh mọi row thuộc đúng train split/fold/subjects.
- Chạy physical eligibility validation trên mọi row.

Artifact tạo ra phải chứa đúng:

- fold ID
- protocol/schema version
- provenance manifest hash
- train-manifest hash
- feature dimension
- train subjects
- sample/frame counts
- mean/std và finite-value policy.

#### Dataset loaders

`RehabDataset` và `SSLRehabDataset` phải:

- tính lại hash của manifest được load;
- so khớp fold metadata và normalization artifact;
- so khớp provenance hash;
- kiểm tra đúng fold và split;
- gọi physical eligibility validation;
- từ chối normalization có mean/std sai chiều, NaN, Inf hoặc std không dương;
- từ chối feature chứa bất kỳ NaN hoặc Inf nào;
- kiểm tra tất cả feature keys/shapes cần cho `__getitem__`, không chỉ `kinematics`.

Đối với val/test Dataset, normalization vẫn phải là artifact được fit từ train manifest của cùng fold. Không được yêu cầu val/test manifest hash bằng train-manifest hash; hãy đối chiếu đúng vai trò qua fold metadata.

### D. Sửa LOSO invariants

1. Thay toàn bộ `assert` về nghiên cứu bằng explicit `if ...: raise ValueError(...)` hoặc exception chuyên biệt.
2. Xác minh expected subject set cụ thể từ configuration, không chỉ đếm đủ 10 chuỗi bất kỳ.
3. Xác minh mỗi subject xuất hiện đúng một lần làm test qua toàn bộ fold.
4. Xác minh train/val/test không giao nhau theo:
   - subject ID
   - sample ID
   - source record ID
   - canonical source-video group
   - source video checksum/identity khi có.
5. Không dùng basename đơn thuần làm unique source identity nếu basename có thể trùng ở hai thư mục.
6. Không âm thầm bỏ record không map được vào train/val/test.
7. Excluded manifest phải có lý do, không được sửa/mutate input record của caller ngoài ý muốn.
8. Hash lưu trong metadata phải đúng với file manifest thực tế sau khi save. Nếu serialization CSV có thể thay đổi kiểu dữ liệu, hãy định nghĩa canonical hashing không phụ thuộc biểu diễn CSV.

### E. Sửa mọi training/pretraining entry point

1. Sửa `training/train.py` để truyền `fold_id` đúng cho cả train và validation Dataset.
2. Kiểm tra tất cả lời gọi `RehabDataset`/`SSLRehabDataset` trong dự án sau khi signature thay đổi.
3. Entry point phải nhận hoặc xác định rõ fold metadata path, không chỉ manifest và normalization path rời rạc.
4. Từ chối swapped train/val/test manifests dựa trên nội dung và hash, không dựa vào tên file.
5. Không dùng substring `extraction_quality` làm hàng rào chính.
6. Không được silently disable requested contrastive pretrained weights khi checkpoint thiếu hoặc sai. Nếu người dùng yêu cầu contrastive mode, command phải fail rõ ràng.

### F. Hoàn thiện checkpoint contract

Tạo một contract và path resolver dùng chung cho save/load.

Checkpoint metadata bắt buộc:

- model ID chuẩn hóa
- fold ID
- protocol/schema version
- provenance manifest hash
- train-manifest hash
- normalization artifact hash
- class mapping
- model configuration/architecture signature
- checkpoint role, ví dụ `pretrained_encoder` hoặc `supervised_model`.

Khi load phải so khớp tất cả giá trị expected tương ứng. Không chỉ kiểm tra sự hiện diện.

Yêu cầu thêm:

- Evaluator phải kiểm tra model ID khớp model đang khởi tạo.
- Pretrained encoder phải được load qua helper an toàn, không gọi `torch.load()` trực tiếp rồi bỏ qua metadata.
- Trainer và evaluator phải lấy path từ cùng một resolver; không lặp chuỗi đường dẫn thủ công ở nhiều file.
- Legacy/raw state-dict checkpoint phải bị từ chối trong strict research mode.
- Không gọi `torch.load()` hai lần trong một expression.

### G. Làm evaluation fail-closed

1. Không catch exception theo cách biến failure thành kết quả thành công.
2. Có thể thu thập lỗi của nhiều model, nhưng sau vòng lặp phải:
   - trả exit code khác 0 nếu bất kỳ required model nào thất bại;
   - không ghi `metrics.json` như một success artifact;
   - nếu cần, ghi file riêng tên rõ ràng như `evaluation_failed.json`.
3. Không tạo confusion matrix hoặc metrics thành công trước khi toàn bộ validation bắt buộc hoàn tất.
4. AUROC không xác định phải được biểu diễn bằng `null`/`NaN` có reason hoặc structured status. Không mặc định `0.0` vì có thể bị hiểu là metric hợp lệ.
5. Completion logits phải qua sigmoid đúng một lần.
6. Exercise logits phải dùng softmax/argmax đúng một lần.
7. Explicit class set phải lấy từ verified class mapping/configuration thay vì hardcode rời rạc nếu checkpoint đã có mapping.
8. Evaluator phải đối chiếu test-manifest hash, fold metadata, normalization artifact và checkpoint metadata trước khi chạm model inference.

## 5. Unit test bắt buộc

Tạo test theo hành vi. Toàn bộ test phải dùng thư mục tạm và dữ liệu nhỏ do test tạo.

### Provenance và hashing

1. Hash idempotent khi record đã có `provenance_hash`.
2. Hash không đổi khi dictionary key order thay đổi.
3. Manifest hash không đổi khi record order thay đổi.
4. Hash không đổi khi cùng relative dataset identity nằm ở hai workspace root khác nhau.
5. Hash thay đổi khi một canonical field thay đổi.
6. Tampered processed file bị phát hiện bằng SHA256 thực tế.
7. Tampered source file bị phát hiện khi source checksum bắt buộc.
8. Checksum không phải hexadecimal bị từ chối.
9. Missing physical file không thể được hợp thức hóa bằng `*_exists=True` trong record.
10. `quality_gate_passed` rỗng/NaN/string false bị từ chối.
11. Record có exclusion reason bị từ chối.
12. Caller tự gán `REAL_VERIFIED` nhưng thiếu verification evidence bị từ chối.

### LOSO

13. Ineligible/mock/rejected/unverified record bị loại hoặc làm generation fail theo contract.
14. Expected subject set sai dù vẫn đủ 10 phần tử phải bị từ chối.
15. Mỗi expected subject làm test đúng một lần.
16. Source group/checksum giao nhau giữa split bị phát hiện bằng exception.
17. Test chứng minh invariants vẫn hoạt động khi Python assert bị vô hiệu hóa hoặc đơn giản xác nhận implementation không dựa vào assert.
18. Input records không bị mutate khi tạo excluded manifest.
19. Hash trong metadata khớp manifest đã save và load lại.

### Normalization và Dataset

20. Normalization từ chối train-manifest hash mismatch.
21. Normalization từ chối provenance hash mismatch.
22. Normalization từ chối val/test row, wrong fold và subject leakage.
23. Normalization từ chối bất kỳ NaN/Inf và feature dimension mismatch.
24. RehabDataset từ chối manifest hash mismatch.
25. RehabDataset từ chối normalization provenance/train hash mismatch.
26. RehabDataset từ chối wrong split/fold, missing feature, invalid label và augmentation trên val/test.
27. RehabDataset từ chối thiếu pose/hand/kinematics keys hoặc sai shape ngay khi khởi tạo.
28. SSL Dataset từ chối dù chỉ một non-train row.
29. SSL Dataset từ chối wrong hash/fold/provenance và missing/invalid feature.

### Entry point và checkpoint

30. Smoke test khởi tạo `training/train.py` tới bước tạo Dataset bằng fixture hợp lệ, chứng minh không còn thiếu `fold_id`.
31. Mọi Dataset constructor call site trong project tương thích signature hiện tại.
32. Swapped train/val manifest bị entry point từ chối.
33. Checkpoint load từ chối mismatch model ID.
34. Checkpoint load từ chối mismatch fold ID.
35. Checkpoint load từ chối mismatch protocol version.
36. Checkpoint load từ chối mismatch provenance hash.
37. Checkpoint load từ chối mismatch train-manifest hash.
38. Checkpoint load từ chối mismatch normalization hash.
39. Checkpoint load từ chối mismatch class mapping/model configuration/role.
40. Pretrained encoder được load bằng strict checkpoint helper.

### Evaluation

41. Missing required checkpoint làm evaluation command thất bại.
42. Một model failure không tạo success `metrics.json`.
43. Khi thu thập nhiều lỗi, command cuối cùng vẫn trả exit code khác 0.
44. Undefined AUROC không bị ghi thành `0.0` hợp lệ.
45. Completion sigmoid được áp dụng đúng một lần.
46. Exercise macro metrics dùng đầy đủ class mapping.
47. Test-manifest/normalization/checkpoint identity mismatch bị phát hiện trước inference.

Không bắt buộc mỗi dòng trên phải là một hàm test riêng, nhưng báo cáo phải map rõ từng mục 1–47 tới test cụ thể và assertion tương ứng. Một test trống hoặc chỉ `pass` được tính là chưa triển khai.

## 6. Trình tự thực hiện

1. Chụp danh sách file và trạng thái ban đầu bằng thao tác read-only.
2. Nếu workspace không phải Git repository, ghi rõ không thể dùng Git để chứng minh thay đổi; không được tuyên bố `git diff clean`.
3. Lập traceability matrix giữa lỗi 1–8, mã cần sửa và test bảo vệ.
4. Sửa canonical hash và physical eligibility trước.
5. Sửa artifact identity chain.
6. Sửa LOSO và normalization.
7. Sửa Dataset loaders và toàn bộ call sites.
8. Sửa checkpoint contract và pretraining load.
9. Sửa evaluation fail-closed.
10. Viết test đầy đủ bằng fixture tạm.
11. Chạy chỉ unit test Stage 2.
12. Có thể chạy syntax/import/static checks nếu không kích hoạt pipeline thật.
13. Kiểm tra không có test artifact bị để lại trong workspace artifact directories.
14. Tạo báo cáo rồi dừng.

## 7. Các lệnh bị cấm

Không chạy:

- extraction trên video thật;
- preprocessing trên feature thật;
- `train.py`, `pretrain.py`, `baseline_trainer.py`, `proposed_trainer.py` như một training job;
- evaluation/inference thật;
- bất kỳ lệnh xóa dữ liệu hoặc checkpoint;
- script tạo lại toàn bộ processed dataset;
- test sử dụng đường dẫn dataset/checkpoint/results thật.

Smoke test entry point chỉ được gọi ở cấp hàm với fixture nhỏ, monkeypatch hợp lý và phải dừng trước training loop/inference.

## 8. Tiêu chí nghiệm thu

Chỉ kết luận `PASS` khi:

1. Cả tám lỗi reviewer được sửa bằng implementation thật.
2. Provenance hash stable, idempotent và portable.
3. Eligibility xác minh physical file/hash trong strict research mode.
4. Artifact identity được đối chiếu xuyên suốt provenance, folds, normalization, Dataset và checkpoint.
5. LOSO không còn dùng `assert` cho invariants nghiên cứu.
6. Tất cả Dataset call sites hoạt động đúng signature và đúng split/fold contract.
7. Pretrained và supervised checkpoint đều dùng strict unified loader.
8. Evaluation trả failure khi bất kỳ required model nào thất bại và không tạo success artifact.
9. Không còn test rỗng hoặc test chỉ có `pass` trong phạm vi Stage 2.
10. Tất cả mục test 1–47 được map tới test có assertion và đều pass.
11. Test chỉ dùng fixture tạm.
12. Không chạy hoặc sửa dữ liệu thật, checkpoint thật và kết quả thật.

Nếu còn một mục chưa đạt, kết luận phải là `FAIL` hoặc `PARTIAL`, không được ghi `PASS`.

## 9. Báo cáo bắt buộc

Tạo file `PHASE_4_7_STAGE_2_CORRECTION_REV2_REPORT.md` tại thư mục gốc dự án, gồm:

1. Executive conclusion: PASS/FAIL/PARTIAL.
2. Danh sách file đã đọc.
3. Danh sách file đã tạo/sửa.
4. Bảng tám lỗi reviewer, cách sửa và test chứng minh.
5. Canonical hashing contract.
6. Physical eligibility contract.
7. Artifact identity chain và các hash được đối chiếu.
8. LOSO invariants.
9. Normalization và Dataset isolation invariants.
10. Checkpoint contract và path resolver.
11. Evaluation failure behavior và exit semantics.
12. Traceability matrix từ test requirement 1–47 đến test name/assertion.
13. Tổng số test collected/passed/failed/skipped.
14. Chính xác mọi command đã chạy.
15. Bằng chứng test chỉ dùng temporary paths.
16. Danh sách artifact ngoài ý muốn; không tự xóa dữ liệu cũ nếu chưa được phép.
17. Remaining risks/unknowns.
18. Stage 3 readiness: `READY` hoặc `NOT READY`, kèm lý do.
19. Compliance statement xác nhận không extraction, preprocessing, training, real evaluation, inference hoặc data deletion.

## 10. Yêu cầu kết thúc

Sau khi tạo báo cáo, dừng hoàn toàn. Không tự động thực hiện Stage 3, không chạy dữ liệu thật và không tuyên bố `PASS` dựa riêng vào số lượng test. `PASS` chỉ hợp lệ khi traceability matrix chứng minh đầy đủ từng tiêu chí nghiệm thu.
