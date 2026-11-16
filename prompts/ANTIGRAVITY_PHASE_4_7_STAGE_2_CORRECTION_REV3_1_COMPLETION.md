# PHASE 4.7 — STAGE 2 CORRECTION REV3.1 COMPLETION

## Vai trò và mục tiêu

Bạn đang tiếp tục công việc còn dang dở của `ANTIGRAVITY_PHASE_4_7_STAGE_2_CORRECTION_REV3_1.md`.

Mục tiêu của lần này là hoàn thiện toàn bộ các yêu cầu còn thiếu, sửa các sai lệch giữa báo cáo và mã nguồn, chạy bộ kiểm thử phù hợp, rồi phát hành báo cáo có bằng chứng. Không được chuyển sang Stage 3 khi bất kỳ tiêu chí bắt buộc nào bên dưới chưa đạt.

## Phạm vi được phép

Bạn được phép:

- Đọc toàn bộ mã nguồn và tài liệu liên quan.
- Sửa mã nguồn, cấu hình và test cần thiết để hoàn thiện REV3.1.
- Chạy unit test, integration test nhẹ, kiểm tra import, static checks và test bằng dữ liệu fixture nhỏ do test tạo trong thư mục tạm.
- Tạo báo cáo kết quả mới.

Bạn không được phép trong nhiệm vụ này:

- Chạy trích xuất MediaPipe trên 491 video thật.
- Xóa, ghi đè hoặc di chuyển dataset hiện có.
- Chạy huấn luyện baseline, RehabMotionNet hoặc LOSO thật.
- Chạy evaluation trên checkpoint nghiên cứu thật.
- Tự tạo dữ liệu giả rồi gắn nhãn `REAL_VERIFIED` để thay thế dữ liệu nghiên cứu.
- Đánh dấu `PASS` nếu chỉ kiểm tra bằng mock, monkeypatch hoặc đọc mã bằng mắt.

Nếu cần fixture cho test, hãy tạo file vật lý nhỏ trong temporary directory, tính SHA-256 thật và đi qua đúng public verification path của hệ thống.

## Nguồn sự thật cần đọc trước khi sửa

Đọc và đối chiếu ít nhất:

- `ANTIGRAVITY_PHASE_4_7_STAGE_2_CORRECTION_REV3_1.md`
- `PHASE_4_7_STAGE_2_CORRECTION_REV3_1_REPORT.md`
- `rehabai/shared/provenance.py`
- `rehabai/training/normalization.py`
- `rehabai/training/checkpoint_utils.py`
- `rehabai/training/datasets/rehab_dataset.py`
- `rehabai/training/datasets/ssl_dataset.py`
- `rehabai/training/train.py`
- `rehabai/training/baseline_trainer.py`
- `rehabai/training/pretrain.py`
- `rehabai/training/proposed_trainer.py`
- `rehabai/training/model_registry.py`
- `rehabai/scripts/evaluate.py`
- `rehabai/scripts/export_model.py`
- `rehabai/tests/test_strict_pipeline.py`
- `rehabai/shared/tests/test_correction_stage2.py`

Tìm toàn bộ call site của các lớp/hàm bị thay đổi bằng tìm kiếm toàn repository. Không được chỉ sửa các file liệt kê ở trên.

## Nhóm 1 — Khôi phục tính tương thích của pipeline training

Hiện chữ ký `RehabDataset` đã có `source_dir`, nhưng ít nhất `training/train.py` vẫn gọi theo chữ ký cũ.

Yêu cầu:

1. Tìm mọi nơi khởi tạo `RehabDataset` và `SSLRehabDataset`.
2. Cập nhật tất cả call site bằng keyword arguments rõ ràng; tránh positional arguments dễ truyền nhầm.
3. Bổ sung `--source-dir` hoặc trường cấu hình tương đương cho mọi entry point cần xác minh source video.
4. Thiếu `source_dir`, manifest, normalization schema hoặc fold metadata phải fail-closed với thông báo rõ ràng.
5. Thêm test gọi entry point hoặc factory thật đủ sâu để phát hiện lỗi chữ ký và thiếu tham số.

Acceptance:

- Không còn call site dùng chữ ký cũ.
- Import và khởi tạo pipeline với fixture hợp lệ thành công.
- Thiếu `source_dir` bị từ chối trước khi training bắt đầu.

## Nhóm 2 — Làm REAL_VERIFIED có thẩm quyền và chống giả mạo

Yêu cầu:

1. Thay kiểm tra kiểu `abspath(...).startswith(root)` bằng containment an toàn dựa trên đường dẫn đã resolve, ví dụ `Path.resolve()` kết hợp `is_relative_to()`, hoặc `os.path.commonpath()` với xử lý Windows đúng cách.
2. Chặn tuyệt đối:
   - `..` path traversal;
   - absolute path trỏ ra ngoài root;
   - sibling-prefix như `data` và `database`;
   - symlink/junction escape khi nền tảng test hỗ trợ;
   - source hoặc processed file không tồn tại.
3. `source_dir` phải bắt buộc trong physical verification path. Không được âm thầm bỏ qua source verification.
4. Dùng timestamp UTC ISO-8601 thật, có timezone, thay cho chuỗi `"now"`.
5. Canonical provenance phải ràng buộc verification evidence bằng một trong hai cách:
   - đưa canonical evidence trực tiếp vào canonical payload; hoặc
   - đưa evidence digest vào canonical payload.
6. Evidence phải chứa tối thiểu identity ổn định theo dataset-relative path, source SHA-256, processed SHA-256, verifier/version, thời điểm xác minh và authority/method.
7. Thay đổi bất kỳ trường evidence quan trọng nào phải làm canonical provenance verification thất bại.
8. Thiếu canonical provenance hash, thiếu evidence, hash sai định dạng, hash file không khớp hoặc authority không hợp lệ đều phải bị từ chối.
9. Không cho phép caller tự khai `REAL_VERIFIED` bằng cách chỉ điền dictionary rồi tự tính lại một hash công khai. Trạng thái này chỉ được cấp qua verification function có kiểm tra hai file vật lý và tạo evidence chuẩn.
10. Giữ một schema/version rõ ràng để có thể phát hiện provenance cũ không còn hợp lệ.

Test bắt buộc dùng file vật lý trong temporary directory:

- valid source + processed fixture được cấp `REAL_VERIFIED`;
- source tampering;
- processed tampering;
- forged evidence;
- evidence field tampering;
- missing evidence/hash;
- traversal;
- sibling-prefix escape;
- absolute external path;
- symlink/junction escape nếu hệ điều hành cho phép tạo; chỉ được skip khi có lý do nền tảng cụ thể được pytest ghi nhận.

## Nhóm 3 — Xác thực shape và contract dữ liệu chính xác

Yêu cầu:

1. Xác định shape contract từ extractor/processor/config hiện tại, không đoán tùy ý.
2. Kiểm tra chính xác rank, frame dimension, landmark count và channel count cho:
   - pose landmarks;
   - left-hand landmarks;
   - right-hand landmarks;
   - kinematics/features.
3. Tất cả modality phải có cùng số frame khi contract yêu cầu.
4. Từ chối object arrays, NaN/Inf, empty sequence và dtype không thể chuyển đổi an toàn.
5. Áp dụng cùng contract cần thiết cho cả supervised và SSL dataset.
6. Không được dùng fixture `(T, 237)` cho mọi modality nếu đó không phải shape thực tế của modality.

Test phải có cả shape hợp lệ và từng loại shape sai riêng biệt.

## Nhóm 4 — Hoàn thiện trainer và checkpoint strict loading

Yêu cầu:

1. Proposed trainer phải đọc và xác minh normalization schema trước khi dùng bất kỳ biến nào từ schema.
2. Pretrained/contrastive encoder phải load qua strict checkpoint loader.
3. Kiểm tra architecture signature, model config, class mapping, fold identity, provenance/manifest hashes và normalization hash theo ngữ cảnh phù hợp.
4. Missing checkpoint hoặc metadata không khớp phải fail-closed, không fallback sang random initialization nếu cấu hình yêu cầu pretrained weights.
5. Baseline trainer, pretrainer, proposed trainer và entry point chính phải dùng cùng contract đã thống nhất.

Test phải thực thi load một checkpoint fixture hợp lệ và từ chối checkpoint có từng metadata quan trọng bị sửa.

## Nhóm 5 — Model registry thật

Yêu cầu:

1. Registry phải hỗ trợ toàn bộ model được pipeline/config hiện tại tham chiếu, gồm các baseline và RehabMotionNet/encoder.
2. Khởi tạo model thật bằng config tối thiểu hợp lệ.
3. Không monkeypatch constructor và không thay model bằng mock trong test registry.
4. Kiểm tra forward pass nhỏ hoặc state-dict compatibility khi hợp lý.
5. Unknown model name và config thiếu/sai phải lỗi rõ ràng.

## Nhóm 6 — Evaluator fail-closed và atomic

Yêu cầu:

1. Preflight toàn bộ jobs trước khi thực hiện inference đầu tiên.
2. Với từng job, xác minh file tồn tại, fold id, split=test, test manifest hash, canonical provenance hash, normalization hash/schema, model config, architecture signature và class mapping.
3. Class list phải explicit và nhất quán; không suy ra tùy tiện từ predictions hoặc test labels.
4. Nếu một job lỗi, không chạy inference cho bất kỳ job nào và không xuất báo cáo thành công một phần.
5. Kết quả chỉ được publish sau khi toàn bộ jobs hoàn tất thành công. Dùng temporary file/directory và atomic replace/rename; dọn file tạm khi thất bại.
6. Nếu completion/regression task chưa được hỗ trợ thì báo cáo phải ghi rõ là omitted/not evaluated; không được tạo metric giả.
7. Không dùng test set để tuning threshold, epoch hoặc hyperparameter.

Test bắt buộc:

- empty jobs;
- một job hợp lệ;
- nhiều job hợp lệ;
- job thứ hai lỗi và chứng minh inference chưa chạy;
- sai fold/test manifest/normalization/class mapping/architecture signature;
- failure giữa quá trình xuất và không có final partial artifact.

## Nhóm 7 — Exporter strict và atomic

Yêu cầu:

1. Không dùng raw `torch.load` ngoài strict checkpoint loader được duyệt.
2. Không tạo dummy/default normalization để lấp metadata thiếu.
3. Lấy expected architecture signature và model config từ nguồn cấu hình/checkpoint đã được xác minh; không truyền `None` khi strict loader yêu cầu giá trị thật.
4. Xác minh checkpoint, fold metadata, normalization schema, hashes và class mapping trước khi trace/export.
5. Dựng toàn bộ export bundle trong temporary directory, bao gồm model và metadata; chỉ publish atomically khi tất cả bước thành công.
6. Nếu lỗi, không để lại bundle hoàn chỉnh giả hoặc file output một phần.

Test phải export một fixture hợp lệ và từ chối metadata mismatch, missing normalization, missing architecture signature và failure giữa quá trình ghi.

## Nhóm 8 — Làm sạch và mở rộng test suite

Yêu cầu:

1. Thay test rỗng chỉ có `pass` bằng assertion có ý nghĩa hoặc xóa khi thực sự trùng lặp và ghi lý do trong báo cáo.
2. Không dùng mock/monkeypatch để chứng minh core provenance, model construction, strict loading, evaluator preflight hoặc exporter hoạt động.
3. Mock chỉ được dùng ở ranh giới phụ như theo dõi xem inference có bị gọi hay không; không được mock chính logic đang kiểm tra.
4. Mỗi bug group phải có ít nhất một positive test và các negative tests đại diện.
5. Chạy collect-only để báo chính xác số test.
6. Chạy các test mục tiêu trước, sau đó chạy toàn bộ test suite Phase 4.7 liên quan.
7. Không được ghi `PASS` nếu có test failure, collection error hoặc unexplained skip.

## Kiểm tra tính nhất quán toàn repository

Trước khi kết luận:

1. Tìm toàn bộ các từ khóa và call site liên quan:
   - `RehabDataset(`, `SSLRehabDataset(`;
   - `REAL_VERIFIED`;
   - `check_physical_eligibility`;
   - `torch.load`;
   - `expected_architecture_signature=None`;
   - test chỉ có `pass`;
   - mock/patch trong các test strict pipeline.
2. Xác minh không còn đường strict nào tự fallback sang giá trị mặc định không có bằng chứng.
3. Xác minh tài liệu và báo cáo khớp với file thực tế được sửa.

## Lệnh kiểm thử và giới hạn tài nguyên

Chỉ chạy kiểm thử nhẹ, không huấn luyện mô hình thật. Ghi lại nguyên văn mọi command đã chạy, exit code và số test passed/failed/skipped.

Nếu full repository test chứa test ngoài phạm vi hoặc phụ thuộc không sẵn có, vẫn phải:

- chạy toàn bộ test Phase 4.7 liên quan;
- liệt kê chính xác test nào không chạy được và lý do;
- không chuyển lỗi môi trường thành `PASS`;
- không cài dependency mới nếu chưa thật sự cần cho phạm vi sửa lỗi.

## Báo cáo bắt buộc

Tạo file:

`PHASE_4_7_STAGE_2_CORRECTION_REV3_1_COMPLETION_REPORT.md`

Báo cáo phải gồm:

1. Executive conclusion: `PASS`, `PARTIAL` hoặc `FAIL`.
2. Stage 3 readiness: `READY` hoặc `NOT READY`.
3. Danh sách đầy đủ file đã tạo/sửa/xóa.
4. Bảng tám bug groups: trạng thái, bằng chứng file:line, test chứng minh.
5. Danh sách command và exit code.
6. Test collection count và passed/failed/skipped.
7. Các lỗi còn tồn tại và mức độ nghiêm trọng.
8. Các giới hạn hoặc test chưa chạy được.
9. Xác nhận không chạy extraction, training, real evaluation và không sửa dataset.
10. Git diff/stat hoặc cách tương đương để chứng minh danh sách file sửa là đầy đủ.

Không được ghi `PASS` chỉ vì code đã được viết. `PASS` chỉ hợp lệ khi cả tám nhóm đáp ứng acceptance criteria và các test bắt buộc tương ứng đều thành công.

## Điều kiện dừng

- Nếu tám nhóm đều PASS và test liên quan đều thành công: tạo báo cáo `PASS`, ghi `Stage 3 readiness: READY`, rồi dừng.
- Nếu còn bất kỳ lỗi nào: tạo báo cáo `PARTIAL` hoặc `FAIL`, ghi `Stage 3 readiness: NOT READY`, liệt kê công việc còn lại, rồi dừng.
- Không tự bắt đầu Stage 3, không chạy LOSO và không xử lý dataset thật.
