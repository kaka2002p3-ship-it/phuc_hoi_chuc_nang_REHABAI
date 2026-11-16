# PHASE 4.7 — STAGE 2 CORRECTION REV3

## 1. Mục tiêu

Hoàn tất các lỗi thực thi và kiểm chứng còn lại của Stage 2 sau REV2. Đây là vòng sửa có phạm vi hẹp: sửa đúng các lỗi đã được reviewer xác nhận, bổ sung test có ý nghĩa và chứng minh pipeline có thể đi vào Stage 3 mà không tạo data leakage hoặc artifact mismatch.

Kết luận hiện tại: `STAGE 2 REV2 = FAIL / PARTIAL IMPLEMENTATION`.

Không được bắt đầu Stage 3 cho đến khi REV3 được reviewer độc lập xác nhận `PASS`.

## 2. Giới hạn bắt buộc

1. Đọc toàn bộ file này trước khi thực hiện.
2. Đọc các prompt và báo cáo Stage 2 trước đó để giữ nguyên các ràng buộc đã được chấp nhận.
3. Chỉ sửa mã hạ tầng và unit test liên quan các lỗi nêu trong REV3.
4. Không chạy extraction, preprocessing, pretraining, training, evaluation hoặc inference thật.
5. Không đọc/xử lý 491 video trong test.
6. Không xóa, đổi tên hoặc ghi đè video, feature, checkpoint, metrics hay báo cáo nghiên cứu hiện có.
7. Tất cả test artifact phải nằm trong `tmp_path`, `tempfile` hoặc thư mục tạm tương đương.
8. Không được dùng test rỗng, `pass`, unconditional skip hoặc test chỉ kiểm tra source-code string thay cho hành vi runtime.
9. Không tự chuyển sang Stage 3.

## 3. File phải kiểm tra

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
- `rehabai/scripts/export_model.py`
- toàn bộ test trong `rehabai/shared/tests/` liên quan Stage 2.

## 4. Công việc bắt buộc

### Task 1 — Sửa mọi Dataset call site

Lỗi hiện tại: `training/train.py` gọi `RehabDataset` nhưng không truyền `fold_id`.

Phải thực hiện:

1. Truyền `fold_id=args.fold_id` cho train và validation Dataset trong `training/train.py`.
2. Tìm toàn bộ lời gọi `RehabDataset(` và `SSLRehabDataset(` trong dự án.
3. Đảm bảo mọi call site truyền đủ tham số theo signature hiện tại.
4. Không thay signature để che giấu lỗi bằng default fold ID.
5. Thêm smoke test cho từng entry point, dừng sau bước tạo Dataset/DataLoader và trước training loop.

### Task 2 — Sửa model registry của evaluator

Lỗi hiện tại: evaluator tham chiếu `MotionNet` và `RehabAI_Model`, trong khi các trainer/model module hiện tại không định nghĩa chắc chắn các tên này.

Phải thực hiện:

1. Tạo một model registry/helper dùng chung ánh xạ canonical `model_id` tới class/model factory thực tế.
2. Dùng đúng các model đã tồn tại, ví dụ các baseline và `RehabMotionNet`, sau khi kiểm tra constructor thật.
3. Trainer và evaluator phải dùng cùng canonical model ID.
4. Model ID không tồn tại phải raise exception trước khi load checkpoint hoặc inference.
5. Không để comment/example import trong production path.
6. Unit test phải instantiate từng registered model bằng configuration tối thiểu và xác nhận evaluator chọn đúng class.

### Task 3 — Hoàn thiện strict checkpoint contract

Checkpoint metadata bắt buộc phải có và được xác minh:

- `model_id`
- `fold_id`
- `protocol_version`
- `provenance_manifest_hash`
- `train_manifest_hash`
- `normalization_hash`
- `class_mapping`
- `model_config`
- `architecture_signature`
- `checkpoint_role`, ví dụ `pretrained_encoder` hoặc `supervised_model`.

Phải thực hiện:

1. Dùng một path resolver duy nhất cho trainer, pretrainer, evaluator và exporter.
2. Validate SHA256 là đúng 64 ký tự hexadecimal, không chỉ kiểm tra độ dài.
3. `load_checkpoint_strict` phải nhận expected values bắt buộc trong research mode và so khớp tất cả trường trên.
4. Model ID, class mapping, model config, architecture signature và role mismatch phải bị từ chối trước `load_state_dict`.
5. Không cho phép expected hash là `None` để bỏ qua kiểm tra trong strict research mode.
6. Legacy/raw state dict phải bị từ chối trong strict research mode.
7. Nếu muốn giữ compatibility ngoài research mode, phải tạo API khác có tên rõ ràng; Stage 3 chỉ được dùng strict API.

### Task 4 — Sửa pretrained encoder loading

Lỗi hiện tại: `proposed_trainer.py` dùng `torch.load()` trực tiếp và gọi hai lần trong một biểu thức. Khi thiếu checkpoint, chương trình tự tắt contrastive.

Phải thực hiện:

1. Xóa direct `torch.load()` khỏi pretrained loading path.
2. Load pretrained encoder qua `load_checkpoint_strict` hoặc helper strict dành riêng cho encoder.
3. Xác minh role là `pretrained_encoder`.
4. Xác minh fold, provenance, train manifest, normalization, model/encoder config và architecture signature.
5. Nếu người dùng bật contrastive nhưng checkpoint thiếu hoặc sai, raise exception; không tự đổi cấu hình model.
6. Việc không sử dụng contrastive chỉ hợp lệ khi cờ cấu hình ban đầu đã tắt nó.

### Task 5 — Làm provenance verification có authority rõ ràng

Lỗi hiện tại: caller có thể tự đặt `data_status=REAL_VERIFIED`; logical gate chưa yêu cầu verification evidence.

Phải thực hiện:

1. Định nghĩa verification contract rõ ràng, tối thiểu gồm:
   - `verification_status`
   - `verification_method`
   - `verified_at`
   - `verified_by` hoặc tool/version authority
   - source checksum
   - processed checksum
   - canonical record hash trước/sau verification nếu cần.
2. Chỉ một verification function riêng mới được cấp `REAL_VERIFIED` sau khi physical integrity và metadata checks đều pass.
3. `build_provenance_record()` chỉ được tạo tối đa `REAL_CANDIDATE`.
4. `check_eligibility()` phải từ chối record tự gán `REAL_VERIFIED` nhưng thiếu verification evidence hợp lệ.
5. Verification function không được tin các cờ `*_exists` trong CSV; phải kiểm tra filesystem và checksum thật.
6. Không cho unit test tự ghi `REAL_VERIFIED` và tự đặt boolean để tạo một “valid” record. Fixture hợp lệ phải đi qua verification function.

### Task 6 — Bắt buộc physical source verification

Lỗi hiện tại: source video chỉ được kiểm tra khi caller tùy chọn truyền `source_dir`; Dataset và normalization không truyền nên source có thể chưa được xác minh.

Phải thực hiện:

1. Canonical manifest phải lưu stable dataset-relative source path hoặc một source identity có thể resolve an toàn.
2. Strict eligibility phải yêu cầu source resolver/root rõ ràng.
3. Kiểm tra source path tồn tại, là file, nằm trong allowed dataset root và checksum khớp.
4. Kiểm tra processed path tồn tại, là file, nằm trong allowed processed root và checksum khớp.
5. Ngăn path traversal và absolute path vượt ra ngoài configured roots.
6. Normalization, supervised Dataset, SSL Dataset và Stage 3 entry points phải gọi strict physical eligibility với source root.
7. Nếu không có source root hoặc không resolve được source identity, phải fail-closed.

### Task 7 — Hoàn thiện fold metadata và artifact identity chain

Lỗi hiện tại: normalization chỉ nhận provenance hash từ metadata rồi chép lại; LOSO metadata chưa chứa hash riêng của train/val/test manifest.

Phải thực hiện:

1. Fold metadata phải chứa:
   - exact expected subject set
   - train subjects, validation subjects, test subject
   - canonical provenance manifest hash
   - canonical train-manifest hash
   - canonical val-manifest hash
   - canonical test-manifest hash
   - per-split sample count
   - protocol/schema version
   - deterministic split rule và seed.
2. Hash phải được tính theo canonical records với vai trò `fold_id` và `split` phù hợp.
3. Khi save CSV rồi load lại, canonical manifest hash phải giữ nguyên.
4. `fit_fold_normalization()` phải tính lại train hash và so với fold metadata trước khi fit.
5. Phải xác minh provenance hash từ nguồn đáng tin cậy; không chỉ chép chuỗi từ metadata.
6. Normalization artifact phải chứa train hash đã xác minh, provenance hash, fold ID, train subjects và finite statistics.
7. `RehabDataset` phải nhận hoặc đọc fold metadata:
   - train Dataset so train hash;
   - val Dataset so val hash;
   - test Dataset so test hash;
   - cả ba so provenance hash và fold identity với normalization/fold metadata.
8. `SSLRehabDataset` chỉ chấp nhận canonical train-manifest hash.
9. Hash mismatch phải xảy ra trước khi tạo DataLoader, training hoặc inference.

### Task 8 — Hoàn thiện True LOSO invariants

Phải thực hiện:

1. Nhận exact expected subject IDs từ configuration, ví dụ danh sách 10 subject cụ thể; không chỉ nhận số `expected_subjects=10`.
2. Từ chối tập có đủ 10 chuỗi nhưng sai subject IDs.
3. Mỗi expected subject phải làm test đúng một lần qua toàn bộ folds.
4. Validation subject phải được chọn deterministic từ các subject ngoài test.
5. Kiểm tra disjoint bằng:
   - subject ID
   - sample ID
   - source record ID
   - stable source path/group ID
   - source video SHA256.
6. Không dùng basename đơn thuần làm canonical source identity nếu tên file có thể lặp ở thư mục khác.
7. Duplicate nguồn phải gây explicit error phù hợp; không được âm thầm loại khiến một subject biến mất rồi chỉ báo lỗi count chung.
8. LOSO research generator phải dùng verified input hoặc strict verification path. Không dùng logical-only record do caller tự khai báo.
9. Mọi record eligible phải được gán đúng một split trong mỗi fold.

### Task 9 — Sửa normalization và Dataset validation còn thiếu

Phải thực hiện:

1. Mean/std phải có đúng feature dimension, là finite và std phải dương sau near-zero handling.
2. Từ chối bất kỳ NaN/Inf nào trong input feature và output statistics.
3. Kiểm tra chính xác shape tối thiểu:
   - `kinematics`: 2D, `(frames, expected_kinematic_dim)`
   - `pose_landmarks`: 3D và đúng landmark/channel count được configuration quy định
   - hand landmarks: 3D và đúng landmark/channel count.
4. Xác minh các modality có cùng frame count trước resampling.
5. Validation diễn ra trong constructor hoặc explicit preflight, trước training/evaluation loop.
6. Không để `IndexError` hoặc broadcasting error thay cho thông báo validation rõ ràng.

### Task 10 — Làm evaluation thực sự fail-closed

Phải thực hiện:

1. Validate toàn bộ config và tất cả jobs trước khi chạy inference job đầu tiên.
2. Từ chối config không có `jobs` hoặc danh sách jobs rỗng.
3. Model registry, fold metadata, test manifest hash, normalization hash và checkpoint metadata phải được kiểm tra trước inference.
4. Nếu bất kỳ required job thất bại:
   - exit code khác 0;
   - không tạo success metrics file;
   - không để lại confusion matrix hoặc partial success artifact;
   - có thể tạo failure artifact riêng với tên và status rõ ràng.
5. Dùng temporary output và atomic rename sau khi toàn bộ jobs hoàn thành.
6. Explicit class mapping phải lấy từ verified checkpoint/config và được đối chiếu.
7. Macro metrics phải dùng toàn bộ expected classes.
8. Undefined metric phải lưu `null` cùng reason/status; không ghi `0.0` như metric hợp lệ.
9. Test completion sigmoid đúng một lần nếu completion task nằm trong evaluator.
10. Nếu evaluator hiện chỉ hỗ trợ exercise classification, báo cáo phải ghi rõ; không được tuyên bố đã kiểm chứng completion metrics.

### Task 11 — Kiểm tra exporter và các đường load model khác

1. Tìm mọi `torch.load()`/`load_state_dict()` trong project.
2. Mọi đường dùng model cho nghiên cứu/evaluation/export phải dùng strict checkpoint contract.
3. `export_model.py` phải xác minh model/fold/provenance/normalization/config trước export.
4. Nếu exporter chưa thuộc phạm vi Phase 4.7, phải fail hoặc được đánh dấu chưa sẵn sàng; không được âm thầm load raw weights.

## 5. Test bắt buộc

Không được chỉ tạo 47 hàm theo số thứ tự. Mỗi test phải có assertion kiểm chứng đúng hành vi. Tạo traceability matrix giữa từng test và yêu cầu dưới đây.

### A. Call-site và model registry

1. `training/train.py` tạo được train/val Dataset với `fold_id` đúng bằng fixture.
2. Baseline trainer tạo đúng Dataset cho train/val.
3. Proposed trainer tạo đúng Dataset cho train/val.
4. Pretrainer tạo đúng SSL train Dataset.
5. Tất cả `RehabDataset` và `SSLRehabDataset` call sites tương thích signature.
6. Model registry tạo đúng class cho từng supported canonical model ID.
7. Unknown model ID bị từ chối trước checkpoint load.

### B. Checkpoint và pretrained loading

8. Save từ chối non-hex hoặc sai độ dài cho mọi SHA256 field.
9. Load từ chối model ID mismatch.
10. Load từ chối fold ID mismatch.
11. Load từ chối protocol mismatch.
12. Load từ chối provenance mismatch.
13. Load từ chối train-manifest mismatch.
14. Load từ chối normalization mismatch.
15. Load từ chối class mapping mismatch.
16. Load từ chối model config mismatch.
17. Load từ chối architecture signature mismatch.
18. Load từ chối checkpoint role mismatch.
19. Raw/legacy checkpoint bị từ chối trong strict mode.
20. Pretrained encoder đi qua strict loader.
21. Thiếu pretrained checkpoint khi contrastive bật phải fail.
22. Contrastive tắt từ configuration không yêu cầu pretrained checkpoint.

### C. Provenance và physical eligibility

23. `build_provenance_record()` không tự cấp `REAL_VERIFIED`.
24. Caller tự sửa `data_status=REAL_VERIFIED` nhưng thiếu evidence bị từ chối.
25. Verification function tạo verified record khi source và processed file/hash hợp lệ.
26. Tampered processed file bị từ chối.
27. Tampered source video bị từ chối.
28. Missing source root bị từ chối trong strict mode.
29. Missing processed/source file không thể được hợp thức hóa bằng boolean trong manifest.
30. Path traversal và path ngoài configured root bị từ chối.
31. Quality boolean rỗng/NaN/string false bị từ chối.
32. Verification evidence thiếu hoặc sai version/authority bị từ chối.

### D. LOSO và artifact hashes

33. Đủ số lượng nhưng sai expected subject set bị từ chối.
34. Duplicate sample ID báo lỗi duplicate rõ ràng.
35. Duplicate source record ID báo lỗi rõ ràng.
36. Cùng source checksum ở hai subject/split bị từ chối.
37. Mỗi subject làm test đúng một lần qua toàn bộ folds.
38. Train/val/test hoàn toàn disjoint theo năm identity dimensions.
39. Mỗi eligible record được gán đúng một split trong mỗi fold.
40. Fold metadata chứa và đối chiếu được train/val/test manifest hashes.
41. Save CSV rồi load lại không đổi canonical manifest hash.
42. Excluded record không làm mutate input caller.

### E. Normalization và Dataset

43. Normalization từ chối train hash mismatch với fold metadata.
44. Normalization từ chối provenance mismatch.
45. Normalization từ chối val/test row và subject leakage.
46. Normalization từ chối NaN/Inf và shape mismatch.
47. Train Dataset từ chối train-manifest hash mismatch.
48. Val Dataset từ chối val-manifest hash mismatch.
49. Test Dataset từ chối test-manifest hash mismatch.
50. Dataset từ chối provenance/normalization/fold mismatch.
51. Dataset từ chối invalid mean/std artifact.
52. Dataset từ chối missing modality key.
53. Dataset từ chối sai pose/hand/kinematic shape.
54. Dataset từ chối frame count lệch giữa modalities.
55. SSL chỉ chấp nhận verified train manifest đúng hash.
56. Augmentation bị từ chối trên val/test.

### F. Evaluation và export

57. Missing config hoặc empty jobs làm exit khác 0.
58. Unknown model làm fail trước inference.
59. Missing checkpoint làm fail và không tạo success output.
60. Một job failure trong nhiều jobs không để lại success/partial metrics.
61. Checkpoint identity mismatch được phát hiện trước inference.
62. Test-manifest hash mismatch được phát hiện trước inference.
63. Undefined metric không bị ghi thành `0.0` hợp lệ.
64. Macro metrics dùng toàn bộ expected classes.
65. Completion sigmoid đúng một lần nếu completion được hỗ trợ.
66. Exporter từ chối raw/mismatched checkpoint.

Không bắt buộc có đúng 66 hàm test, nhưng mọi mục phải được map tới test có assertion thật. Không dùng một test không liên quan để tuyên bố đã bao phủ một yêu cầu.

## 6. Verification được phép

Được phép:

- đọc/search mã nguồn;
- chạy syntax/import/static checks;
- chạy unit test Stage 2 bằng fixture tạm;
- chạy smoke test cấp hàm dừng trước training/inference;
- kiểm tra filesystem read-only để chắc chắn test không ghi vào artifact directories.

Không được phép:

- chạy pipeline extraction/preprocessing thật;
- chạy training/pretraining/evaluation/inference thật;
- tạo hoặc sửa checkpoint/metrics thật;
- xóa dữ liệu hoặc artifact cũ;
- dùng video hoặc feature thật làm fixture.

## 7. Điều kiện PASS

Chỉ ghi `PASS` khi đồng thời thỏa:

1. Tất cả 11 task ở mục 4 được hoàn thành.
2. Không còn Dataset call site sai signature.
3. Evaluator dùng model registry thật và instantiate được tất cả supported models.
4. Pretrained loading không còn direct `torch.load()` hoặc silent fallback.
5. Checkpoint strict loader xác minh đầy đủ identity/config/role.
6. `REAL_VERIFIED` chỉ được tạo qua verification function có physical evidence.
7. Source và processed file/hash được kiểm tra trong strict pipeline.
8. Fold metadata có hash riêng của train/val/test và được đối chiếu xuyên suốt.
9. True LOSO kiểm tra exact subject set và source checksum isolation.
10. Evaluation fail-closed, không để lại success artifact khi có lỗi.
11. Không còn test rỗng, test chỉ `pass` hoặc test gắn sai requirement.
12. Tất cả test requirement 1–66 có test/assertion tương ứng và pass.
13. Không chạy dữ liệu thật và không ghi vào artifact directories thật.

Nếu còn bất kỳ mục nào chưa đạt, kết luận phải là `FAIL` hoặc `PARTIAL`.

## 8. Báo cáo bắt buộc

Tạo `PHASE_4_7_STAGE_2_CORRECTION_REV3_REPORT.md` tại thư mục gốc dự án, gồm:

1. Executive conclusion: PASS/FAIL/PARTIAL.
2. File đã đọc, tạo và sửa.
3. Bảng 11 task, implementation location và test evidence.
4. Dan exact changes cho từng lỗi reviewer.
5. Model registry và supported canonical model IDs.
6. Checkpoint schema, path resolver và strict load contract.
7. `REAL_VERIFIED` issuance/authority contract.
8. Physical source/processed integrity contract.
9. Fold metadata và artifact identity chain.
10. LOSO invariants và expected subject configuration.
11. Evaluation failure/exit/output semantics.
12. Traceability matrix từ requirement test 1–66 tới test name và assertion chính.
13. `pytest --collect-only` count và kết quả test thực tế.
14. Số passed/failed/skipped/xfailed; mọi skipped/xfailed phải giải thích và không được tính PASS nếu thuộc requirement.
15. Chính xác các command đã chạy.
16. Bằng chứng mọi test dùng temporary fixture.
17. Bằng chứng không chạy pipeline hoặc dữ liệu thật.
18. Remaining risks/unknowns.
19. Stage 3 readiness: READY/NOT READY với lý do.
20. Compliance statement.

Không được gọi số lượng test là “code coverage 100%” nếu không chạy công cụ coverage và không có báo cáo line/branch coverage. Có thể ghi “66/66 acceptance requirements mapped and passed” nếu có traceability evidence đúng.

## 9. Yêu cầu kết thúc

Sau khi hoàn thành và tạo báo cáo, dừng hoàn toàn. Không tự động chạy Stage 3, không chạy dữ liệu thật và không tự tuyên bố pipeline khoa học hoàn thiện ngoài phạm vi đã được test.
