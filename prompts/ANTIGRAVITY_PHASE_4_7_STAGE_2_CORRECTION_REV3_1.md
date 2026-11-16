# PHASE 4.7 — STAGE 2 CORRECTION REV3.1

## Mục tiêu

Sửa dứt điểm các lỗi chặn còn lại sau Stage 2 Correction REV3. Đây là vòng sửa tập trung. Không viết lại toàn bộ pipeline và không mở rộng sang Stage 3.

Trạng thái reviewer hiện tại: `REV3 = FAIL / PARTIAL`, mức hoàn thiện Stage 2 ước tính 75–80%.

Chỉ được kết luận `PASS` khi implementation thật hoạt động nhất quán và test kiểm chứng đúng hành vi, không dựa riêng vào số lượng hàm test.

## Quy tắc bắt buộc

1. Đọc toàn bộ file này trước khi sửa.
2. Đọc lại:
   - `ANTIGRAVITY_PHASE_4_7_STAGE_2_CORRECTION_REV3.md`
   - `PHASE_4_7_STAGE_2_CORRECTION_REV3_REPORT.md` nếu đã được đặt trong dự án
   - toàn bộ file được nêu trong prompt này.
3. Không chạy extraction, preprocessing, pretraining, training, evaluation hoặc inference thật.
4. Không đọc/xử lý 491 video thật trong test.
5. Không xóa, đổi tên hoặc ghi đè dữ liệu, feature, checkpoint, metrics hay báo cáo nghiên cứu hiện có.
6. Unit test chỉ được sử dụng `tmp_path`, `tempfile` hoặc thư mục tạm tương đương.
7. Không được dùng `pass`, unconditional skip, test chỉ tìm chuỗi source code hoặc mock chính hành vi cần kiểm chứng.
8. Không tự chuyển sang Stage 3.

## Các lỗi chặn phải sửa

### 1. Thống nhất artifact hash schema

Lỗi hiện tại:

- `training/normalization.py` ghi `train_manifest_hash`.
- `RehabDataset`, `SSLRehabDataset` và một số trainer lại đọc `canonical_train_manifest_hash`.
- Dataset muốn kiểm tra val/test hash nhưng normalization artifact chưa lưu chúng.

Yêu cầu:

1. Định nghĩa một schema duy nhất cho fold metadata và normalization metadata. Không dùng hai tên khác nhau cho cùng một hash.
2. Khuyến nghị canonical keys:
   - `canonical_provenance_manifest_hash`
   - `canonical_train_manifest_hash`
   - `canonical_val_manifest_hash`
   - `canonical_test_manifest_hash`
   - `normalization_artifact_hash` chỉ dùng ngoài chính file normalization để tránh self-hash.
3. `generate_loso.py` phải tạo bốn manifest hashes trên từ canonical records.
4. `fit_fold_normalization()` phải:
   - tính lại train hash;
   - so với fold metadata;
   - lưu nguyên vẹn provenance/train/val/test hashes đã xác minh vào normalization metadata.
5. `RehabDataset` phải chọn đúng expected hash theo split:
   - train → canonical train hash;
   - val → canonical val hash;
   - test → canonical test hash.
6. `SSLRehabDataset` chỉ dùng canonical train hash.
7. Trainer, pretrainer, evaluator và checkpoint phải dùng cùng key names.
8. Thêm schema validator/helper dùng chung để tránh mỗi file tự đọc key theo cách khác.

### 2. Bắt buộc xác minh source video trong strict mode

Lỗi hiện tại: `check_physical_eligibility()` cho phép `source_dir=None`; normalization và Dataset chỉ truyền processed directory nên source video không được kiểm tra.

Yêu cầu:

1. Strict research mode phải bắt buộc cả `source_root` và `processed_root`.
2. `RehabDataset`, `SSLRehabDataset` và `fit_fold_normalization()` phải nhận hai root này hoặc một verified resolver/config object.
3. Thiếu một trong hai root phải fail trước khi load feature.
4. Resolve source bằng stable dataset-relative path, không chỉ basename.
5. Xác minh source và processed path:
   - tồn tại;
   - là file;
   - nằm trong allowed root;
   - checksum SHA256 khớp manifest.
6. Dùng `Path.resolve()` kết hợp `Path.is_relative_to()` hoặc `os.path.commonpath()` để kiểm tra root. Không dùng string `startswith()`.
7. Từ chối path traversal, sibling-prefix path và symlink escape.

### 3. Làm quyền cấp `REAL_VERIFIED` không thể tự khai báo

Lỗi hiện tại: caller có thể tạo `verification_evidence={"verified_by": "strict_pipeline_v1"}` và tự đặt `data_status=REAL_VERIFIED`.

Yêu cầu:

1. `build_provenance_record()` chỉ tạo tối đa `REAL_CANDIDATE`.
2. Chỉ `verify_and_grant_real_verified()` được cấp `REAL_VERIFIED` sau khi kiểm tra vật lý source/processed files và metadata.
3. Verification evidence tối thiểu gồm:
   - `verification_schema_version`
   - `verification_status`
   - `verification_method`
   - `verified_by`
   - timestamp UTC ISO-8601 thật
   - source SHA256
   - processed SHA256
   - source relative identity
   - processed relative identity.
4. Sau verification, canonical record phải được cập nhật bằng các checksum thực tế; không để checksum rỗng.
5. Verification evidence hoặc deterministic digest của evidence phải được ràng buộc vào canonical provenance hash.
6. `check_eligibility()` phải kiểm tra đầy đủ evidence fields, checksums và canonical hash integrity. Chỉ kiểm tra chuỗi `verified_by` là không đủ.
7. Không parse dictionary từ chuỗi bằng một cơ chế mơ hồ. Canonical CSV/JSON serialization phải được định nghĩa rõ.
8. Unit-test fixture hợp lệ phải được tạo bằng verification function, không được tự gán `REAL_VERIFIED` hoặc tự dựng evidence.

### 4. Sửa lỗi thứ tự `norm_schema` trong proposed trainer

Lỗi hiện tại: `proposed_trainer.py` dùng `norm_schema` trong strict pretrained load trước khi đọc file normalization.

Yêu cầu:

1. Đọc và validate normalization schema trước mọi sử dụng.
2. Tính/đọc expected hashes trước khi load pretrained checkpoint.
3. Nếu contrastive bật và checkpoint thiếu/sai, fail rõ ràng.
4. Nếu contrastive tắt từ CLI/config, không yêu cầu pretrained checkpoint.
5. Không tự thay đổi `args.use_contrastive` khi runtime gặp lỗi.
6. Thêm smoke test thực sự chạy code path đến sau strict pretrained load bằng fixture, nhưng dừng trước training loop.

### 5. Hoàn thiện model registry

Lỗi hiện tại: registry ánh xạ `MotionNet` sang `BiLSTMBaseline`, đồng thời không bao phủ nhất quán các model IDs mà baseline trainer lưu.

Yêu cầu:

1. Liệt kê canonical model IDs thực tế được Phase 4.7 hỗ trợ.
2. Mỗi ID ánh xạ tới đúng class và constructor thật:
   - các baseline hiện có;
   - `RehabMotionNet`;
   - encoder nếu cần checkpoint riêng.
3. Trainer, checkpoint path resolver và evaluator phải dùng cùng ID.
4. Không dùng alias gây hiểu nhầm như `MotionNet` → `BiLSTMBaseline` trừ khi có tài liệu canonical rõ ràng.
5. Model config phải tái tạo đúng kiến trúc đã save.
6. Test phải instantiate model class thật với fixture/config tối thiểu. Không mock constructor trong test xác nhận registry.
7. Với model quá nặng, được phép kiểm tra kiểu/class và state-dict compatibility trên CPU mà không chạy training.

### 6. Hoàn thiện evaluator fail-closed

Lỗi hiện tại:

- `jobs=[]` có thể được coi là thành công.
- Chưa preflight toàn bộ jobs trước inference.
- Macro metrics không truyền explicit expected class list.
- Output chưa atomic.
- Chưa liên kết test manifest với fold metadata đáng tin cậy.

Yêu cầu:

1. Config thiếu `jobs` hoặc `jobs=[]` phải fail.
2. Thực hiện preflight cho toàn bộ jobs trước job inference đầu tiên:
   - model ID/config hợp lệ;
   - fold metadata tồn tại và hợp lệ;
   - test manifest hash khớp fold metadata;
   - normalization hashes khớp fold metadata;
   - checkpoint metadata khớp;
   - source/processed roots hợp lệ;
   - output paths hợp lệ.
3. Không lấy expected hashes chỉ từ chính eval config mà không đối chiếu fold metadata/canonical artifacts.
4. Nếu bất kỳ preflight hoặc job nào lỗi:
   - exit code khác 0;
   - không tạo success metrics;
   - không để lại partial output;
   - không đổi tên temporary output thành final output.
5. Ghi output qua temporary file và atomic replace sau khi tất cả jobs thành công.
6. Macro precision/recall/F1 phải dùng explicit class list từ verified class mapping.
7. Trường hợp class vắng mặt hoặc metric không xác định phải được biểu diễn rõ, không gây hiểu nhầm.
8. Nếu evaluator chỉ đánh giá exercise classification, báo cáo phải nói rõ completion task chưa được đánh giá trong Stage 2.

### 7. Sửa exporter

Lỗi hiện tại: `scripts/export_model.py` vẫn dùng raw `torch.load()` và tạo normalization giả khi thiếu file.

Yêu cầu:

1. Xóa raw checkpoint loading khỏi strict export path.
2. Dùng model registry, checkpoint path resolver và `load_checkpoint_strict()`.
3. Xác minh fold, model ID/config, architecture signature, checkpoint role, provenance, train manifest, normalization và class mapping trước export.
4. Thiếu normalization phải fail; tuyệt đối không tạo zero-mean/one-std dummy normalization.
5. Thiếu metrics hợp lệ phải được ghi rõ hoặc fail theo contract; không tạo model card gây hiểu nhầm.
6. Exporter phải dùng artifact tạm và atomic publish sau khi toàn bộ validation pass.
7. Unit test phải chứng minh raw/mismatched checkpoint và missing normalization đều bị từ chối trước khi TorchScript export.

### 8. Sửa bộ test và báo cáo

Lỗi hiện tại:

- Vẫn có test chỉ chứa `pass`.
- Test LOSO overlap mong lỗi subject mismatch thay vì kiểm tra overlap.
- Fixture tự giả lập `REAL_VERIFIED`.
- Registry test mock constructors.
- Nhiều yêu cầu REV3 chưa có test tương ứng dù file có 66 hàm.

Yêu cầu:

1. Xóa hoặc thay thế mọi test rỗng/`pass` bằng assertion thực sự.
2. Không đặt tên test theo requirement rồi kiểm tra một hành vi khác.
3. Test duplicate/overlap phải xác nhận đúng exception và nguyên nhân cụ thể.
4. Fixture verified phải đi qua verification function với source/processed files tạm và checksum thật.
5. Test registry phải instantiate class thật.
6. Bổ sung test tối thiểu cho:
   - hash key consistency giữa fold/normalization/Dataset/checkpoint;
   - train/val/test manifest hash validation;
   - mandatory source root;
   - source checksum tampering;
   - path traversal, sibling-prefix và symlink escape;
   - forged verification evidence;
   - proposed trainer contrastive smoke path;
   - tất cả supported model IDs;
   - empty evaluation jobs;
   - multi-job preflight/failure không tạo output;
   - explicit macro class list;
   - exporter strict checkpoint và missing normalization;
   - call-site compatibility.
7. Không dùng “100% coverage” nếu không chạy công cụ code coverage có line/branch report.
8. Báo cáo phải chứa traceability matrix thật: requirement → test name → assertion → implementation location.

## Test tối thiểu phải thu thập

Không bắt buộc đúng một con số cố định. Số test phải phản ánh hành vi thật. Tất cả nhóm sau phải có test:

1. Artifact schema/key round trip.
2. Fold → normalization hash binding.
3. Train/val/test Dataset hash binding.
4. Source và processed physical integrity.
5. REAL_VERIFIED issuance và forged-evidence rejection.
6. LOSO exact subject set và five-dimensional disjointness.
7. Proposed trainer contrastive strict load.
8. Model registry real instantiation.
9. Checkpoint metadata mismatch cho mọi field.
10. Empty/multi-job evaluation fail-closed.
11. Explicit-class macro metrics.
12. Strict exporter failure paths.
13. Không có test rỗng, skip hoặc mock hành vi cốt lõi.

## Trình tự thực hiện

1. Lập bảng key/schema hiện đang được từng file đọc và ghi.
2. Chọn schema canonical duy nhất và sửa producer trước consumer.
3. Sửa provenance verification và mandatory roots.
4. Sửa LOSO/fold metadata và normalization.
5. Sửa Dataset consumers.
6. Sửa trainer/pretrainer/model registry/checkpoint paths.
7. Sửa evaluator.
8. Sửa exporter.
9. Viết lại những test sai và bổ sung test còn thiếu.
10. Chạy chỉ unit test/smoke test bằng temporary fixtures.
11. Kiểm tra không có artifact bị ghi vào thư mục thật.
12. Tạo báo cáo rồi dừng.

## Các lệnh bị cấm

Không chạy:

- extraction hoặc preprocessing dữ liệu thật;
- pretraining/training thật;
- evaluation/inference thật;
- export model thật;
- lệnh xóa dữ liệu/checkpoint/artifact;
- test sử dụng video, `.npz`, checkpoint hoặc results thật.

## Điều kiện PASS

Chỉ kết luận `PASS` khi:

1. Tám nhóm lỗi trên đã được sửa bằng implementation thật.
2. Normalization artifact được Dataset train/val/test và trainer đọc đúng schema.
3. Source video verification là bắt buộc trong strict pipeline.
4. Không thể cấp `REAL_VERIFIED` chỉ bằng sửa dictionary/CSV fields.
5. Proposed trainer contrastive path không còn lỗi biến chưa khởi tạo.
6. Registry tái tạo đúng tất cả supported models mà không mock.
7. Evaluation preflight/fail-closed/atomic output hoạt động.
8. Exporter không còn raw load hoặc dummy normalization.
9. Không còn test rỗng, test sai mục tiêu hoặc fixture tự giả verification.
10. Tất cả test liên quan pass và không có skipped/xfailed requirement.
11. Không chạy/chạm dữ liệu thật hoặc artifact thật.

Nếu còn bất kỳ mục nào chưa đạt, phải ghi `FAIL` hoặc `PARTIAL`.

## Báo cáo bắt buộc

Tạo `PHASE_4_7_STAGE_2_CORRECTION_REV3_1_REPORT.md` tại thư mục gốc dự án, gồm:

1. Executive conclusion: PASS/FAIL/PARTIAL.
2. Danh sách file đã đọc, tạo, sửa.
3. Bảng schema keys trước/sau và producer/consumer tương ứng.
4. Bảng tám nhóm lỗi, implementation location và test evidence.
5. REAL_VERIFIED verification contract.
6. Source/processed root và path-containment contract.
7. Fold/normalization/Dataset/checkpoint hash chain.
8. Supported canonical model IDs và class mapping.
9. Evaluation preflight, failure và atomic output behavior.
10. Exporter strict behavior.
11. Traceability matrix requirement → test → assertion → implementation.
12. `pytest --collect-only` output và kết quả test.
13. Tổng passed/failed/skipped/xfailed.
14. Chính xác mọi command đã chạy.
15. Bằng chứng fixture chỉ nằm trong temporary directories.
16. Bằng chứng không chạy dữ liệu/pipeline thật.
17. Remaining risks/unknowns.
18. Stage 3 readiness: READY/NOT READY với lý do.
19. Compliance statement.

Không được ghi “100% coverage” nếu không có báo cáo coverage line/branch. Không được coi tên test hoặc test pass rỗng là bằng chứng nghiệm thu.

## Kết thúc

Sau khi tạo báo cáo, dừng hoàn toàn. Không chạy Stage 3 và không tự động xử lý dữ liệu thật.
