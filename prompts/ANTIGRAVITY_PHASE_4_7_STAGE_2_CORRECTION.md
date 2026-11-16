# PHASE 4.7 — STAGE 2 CORRECTION

## Mục đích

Sửa phần triển khai Stage 2 hiện tại để các hàng rào chống data leakage, synthetic/mock contamination, sai fold và test-set misuse được **thực thi bằng mã nguồn**, không chỉ được mô tả trong báo cáo hoặc giả định từ tên tham số.

Stage 2 hiện tại **chưa đạt PASS**. Không được bắt đầu Stage 3 cho đến khi toàn bộ tiêu chí trong prompt này đạt yêu cầu và được chứng minh bằng unit test.

## Quy tắc bắt buộc

1. Đọc toàn bộ prompt này trước khi sửa.
2. Đọc các file sau để hiểu trạng thái hiện tại:
   - `ANTIGRAVITY_PHASE_4_7_STAGE_2_PIPELINE_HARDENING.md`
   - `PHASE_4_7_STAGE_2_REPORT.md` nếu file đã được đặt trong dự án
   - `rehabai/shared/provenance.py`
   - `rehabai/scripts/generate_loso.py`
   - `rehabai/training/normalization.py`
   - `rehabai/training/datasets/rehab_dataset.py`
   - `rehabai/training/datasets/ssl_dataset.py`
   - `rehabai/training/train.py`
   - `rehabai/training/pretrain.py`
   - `rehabai/training/evaluate_baselines.py`
   - toàn bộ test liên quan Stage 2.
3. Chỉ sửa lớp hạ tầng, validation, manifest, provenance, dataset loader và unit test của Stage 2.
4. **Không chạy extraction trên video thật.**
5. **Không chạy preprocessing trên dữ liệu thật.**
6. **Không chạy pretraining, supervised training, evaluation hoặc inference thật.**
7. **Không xóa, đổi tên hoặc ghi đè** video, `.npz`, `.h5`, checkpoint, metric hay báo cáo kết quả hiện có.
8. Unit test chỉ được dùng dữ liệu fixture nhỏ trong thư mục tạm của test. Không tạo file test trong `data/`, `training/checkpoints/`, `data/models/weights/` hoặc các thư mục kết quả thật.
9. Không được sửa test để hợp thức hóa hành vi sai. Hãy sửa mã nguồn để thỏa hợp đồng nghiên cứu.
10. Nếu phát hiện yêu cầu mâu thuẫn hoặc thiếu thông tin khiến không thể triển khai an toàn, dừng đúng phần bị ảnh hưởng và ghi rõ trong báo cáo. Không tự suy đoán để nới lỏng hàng rào.

## Các lỗi đã được reviewer xác nhận

### 1. LOSO chưa thực thi eligibility gate

`generate_loso.py` nhận biến có tên `eligible_records` nhưng không tự kiểm tra eligibility. Bản ghi mock, rejected, quality fail hoặc thiếu file vẫn có thể được đưa vào fold nếu caller truyền trực tiếp.

### 2. Normalization tin tưởng caller

`fit_fold_normalization()` không chứng minh manifest đầu vào chỉ chứa train samples của đúng fold. Validation hoặc test manifest có thể được dùng để fit thống kê.

### 3. SSL chấp nhận non-train rows

`ssl_dataset.py` phát hiện dòng có `split != train` nhưng chỉ thực hiện `pass`. Điều này không chặn validation/test khỏi self-supervised learning.

### 4. Supervised Dataset chưa kiểm tra hợp đồng nghiên cứu

`rehab_dataset.py` không bắt buộc và không đối chiếu đầy đủ `data_status`, extraction status, quality gate, subject, split, fold, provenance identity và normalization identity.

### 5. Provenance builder chưa hoàn chỉnh

`provenance.py` chủ yếu tạo một record từ đối số và đặt nhiều giá trị mặc định. Nó chưa đối soát chắc chắn metadata gốc, extraction log, file nguồn, interim/processed feature và checksum để tạo canonical provenance manifest.

### 6. Evaluation chưa fail-closed

CLI evaluation bắt exception của model/checkpoint rồi vẫn có thể ghi file kết quả và kết thúc thành công. Một lần evaluation thiếu checkpoint hoặc sai hợp đồng dữ liệu phải trả exit code khác 0 và không được tạo báo cáo thành công gây hiểu nhầm.

### 7. Quy ước checkpoint không thống nhất

Trainer và evaluator hiện không đảm bảo dùng cùng thư mục, tên file, model identifier và fold identifier.

### 8. Bộ test chưa đủ

Mười test hiện tại không chứng minh được các hàng rào quan trọng. Một số test chỉ kiểm tra happy path hoặc tạo fixture nhưng không đưa fixture gây leakage vào hàm cần kiểm tra.

## Công việc phải thực hiện

### A. Xây dựng canonical provenance manifest

Hoàn thiện `rehabai/shared/provenance.py` hoặc tách module rõ ràng nếu cần.

Canonical provenance record tối thiểu phải có:

- `sample_id`
- `source_record_id`
- `source_video_path`
- `source_video_sha256`
- `subject_id`
- `exercise_id`
- `label`
- `label_source`
- `subject_source`
- `interim_feature_path`
- `processed_feature_path`
- `processed_feature_sha256`
- `extractor_name`
- `extractor_version`
- `extraction_status`
- `quality_gate_passed`
- `data_status`
- `generation_script`
- `feature_shape`
- `frame_count`
- `created_at`
- `exclusion_reasons`

Yêu cầu:

1. Builder phải đọc và đối soát metadata/index, extraction-quality log và file trên đĩa; không được mặc định `extraction_log_present=True` hoặc gán nguồn nhãn/chủ thể khi chưa có bằng chứng.
2. Chuẩn hóa kiểu dữ liệu trước khi kiểm tra: chuỗi rỗng, `NaN`, `None`, subject ID, exercise ID, boolean và status.
3. `MOCK` phải thắng mọi trạng thái khác nếu extractor/version/generation evidence cho thấy mock hoặc synthetic.
4. `REJECTED` khi extraction không success hoặc quality gate không pass.
5. `REAL_CANDIDATE` chỉ khi có bằng chứng extraction thật, quality pass, source file và processed feature tồn tại, metadata hợp lệ.
6. `REAL_VERIFIED` chỉ được cấp qua một bước verification rõ ràng sau khi toàn bộ bằng chứng bắt buộc được kiểm tra. Không tự động nâng cấp chỉ vì hai file tồn tại.
7. Tạo stable provenance manifest hash từ canonical content. Việc tính hash phải deterministic và không phụ thuộc thứ tự dictionary hoặc thứ tự đọc file.
8. Trùng `sample_id`, xung đột subject/label/source hoặc ánh xạ một processed feature tới nhiều source phải gây lỗi rõ ràng.
9. Không sửa hoặc xóa feature thật trong quá trình xây manifest.

### B. Một eligibility gate duy nhất và fail-closed

Tạo một API dùng chung, ví dụ `validate_research_eligibility(record)` và `filter_or_reject_manifest(...)`.

Một sample chỉ hợp lệ cho mô hình khi đồng thời thỏa:

- `data_status == REAL_VERIFIED`
- `extraction_status == success`
- `quality_gate_passed == true`
- source video tồn tại
- processed feature tồn tại
- checksum bắt buộc có định dạng hợp lệ
- `subject_id` thuộc tập subject dự kiến
- `exercise_id` thuộc tập nhãn được cấu hình
- label hợp lệ, không rỗng và không bị ép kiểu âm thầm
- không có exclusion reason
- không trùng `sample_id`
- không xung đột `source_record_id` hoặc source-video group.

Không dùng `assert` cho validation ảnh hưởng tính đúng đắn nghiên cứu. Hãy raise exception có loại và thông báo rõ ràng vì Python có thể vô hiệu hóa `assert`.

LOSO generator, normalization, supervised Dataset và SSL Dataset phải gọi hàng rào dùng chung này; không được chỉ tin caller.

### C. Sửa True LOSO generator

Sửa `rehabai/scripts/generate_loso.py` để:

1. Nhận canonical provenance manifest và tự xác nhận manifest/hash/version.
2. Từ chối toàn bộ record không eligible; mặc định fail-closed. Nếu có chế độ loại record, phải xuất exclusion manifest đầy đủ và không được âm thầm bỏ qua.
3. Xác nhận chính xác tập subject dự kiến. Subject thiếu, dư, rỗng hoặc sai định dạng phải gây lỗi.
4. Tạo đúng một test subject cho mỗi fold; sau 10 fold, mỗi subject xuất hiện đúng một lần ở test.
5. Validation subject chỉ được chọn từ 9 subject không phải test theo quy tắc deterministic đã ghi trong metadata.
6. Train, validation và test không giao nhau theo:
   - `sample_id`
   - `source_record_id`
   - canonical source-video group
   - subject.
7. Mọi row được lưu phải có `fold_id` và `split` rõ ràng.
8. Mỗi fold phải có `metadata.json` chứa tối thiểu:
   - protocol name/version
   - fold ID
   - test subject
   - validation subject(s)
   - train subjects
   - deterministic seed/rule
   - canonical provenance manifest hash
   - input record count
   - eligible count
   - excluded count
   - per-split sample count
   - timestamp hoặc build identifier.
9. File đầu ra phải deterministic với cùng input và configuration.
10. Không dùng đường dẫn hoặc subject list hardcoded ngoài configuration có kiểm tra.

### D. Khóa normalization theo đúng fold và train split

Sửa `rehabai/training/normalization.py` để hàm fit cần đồng thời nhận hoặc đọc:

- train manifest của fold
- fold metadata
- canonical provenance hash
- output path trong khu vực fixture hoặc artifact được chỉ định.

Trước khi fit phải xác nhận:

1. Tất cả row có đúng `fold_id`.
2. Tất cả row có `split == train`.
3. Không subject nào thuộc validation/test của fold.
4. Manifest hash khớp metadata.
5. Mọi sample qua eligibility gate.
6. Không có duplicate hoặc missing feature.

Normalization artifact phải lưu:

- schema/protocol version
- fold ID
- train subjects theo thứ tự deterministic
- provenance manifest hash
- train-manifest content hash
- feature count/dimension
- sample count
- frame count
- mean/std
- near-zero-variance handling rule
- creation metadata cần thiết để tái lập.

Phải từ chối NaN/Inf, vector sai chiều, all-NaN feature và artifact có schema không hợp lệ.

### E. Khóa supervised Dataset

Sửa `rehabai/training/datasets/rehab_dataset.py` để:

1. Bắt buộc canonical schema, bao gồm `subject_id`, `fold_id`, `split`, provenance fields và eligibility fields.
2. Xác nhận mọi row đúng split được yêu cầu và đúng fold.
3. Gọi eligibility gate cho từng sample.
4. Đối chiếu normalization artifact với fold ID, train-manifest hash/provenance hash và feature dimension.
5. Chỉ cho phép augmentation khi `split == train`; yêu cầu augmentation ở validation/test phải raise exception.
6. Nhãn completion/exercise không hợp lệ phải raise exception, không được âm thầm đổi thành 0 hoặc trừ 1 thành nhãn sai.
7. Từ chối missing file, duplicate ID, NaN/Inf và feature shape không tương thích.
8. Không chấp nhận legacy extraction-quality CSV hoặc manifest thiếu schema chỉ vì có vài cột trùng tên.

### F. Khóa SSL Dataset

Sửa `rehabai/training/datasets/ssl_dataset.py` để:

1. Chỉ chấp nhận row có `split == train` của đúng fold.
2. Gặp bất kỳ validation/test/unknown split nào phải raise exception ngay; xóa logic `pass` hiện tại.
3. Gọi eligibility gate.
4. Đối chiếu normalization và provenance identity giống supervised Dataset.
5. Từ chối manifest thiếu split/fold/canonical schema.
6. Chỉ tạo augmentation views sau khi toàn bộ manifest đã được xác nhận là train-only.

### G. Guard cho train, pretrain và evaluation

Sửa các entry point để:

1. Yêu cầu explicit fold directory hoặc fold ID, canonical manifests, metadata và normalization artifact.
2. Xác nhận train loader chỉ dùng train manifest; validation loader chỉ dùng validation manifest; evaluator chỉ dùng test manifest.
3. Không dựa vào việc tên file có chứa `extraction_quality` để nhận biết manifest sai. Phải xác nhận schema và content.
4. Chuẩn hóa checkpoint contract dùng chung, gồm model ID, fold ID, protocol version và expected path. Trainer và evaluator phải dùng cùng helper.
5. Checkpoint phải chứa metadata tối thiểu: model ID, fold ID, provenance hash, normalization/train-manifest hash, class mapping và model configuration.
6. Khi load, evaluator phải đối chiếu metadata checkpoint với fold/test manifest/normalization.
7. Thiếu hoặc sai checkpoint phải khiến command thất bại với exit code khác 0.
8. Nếu một model bắt buộc thất bại, không được ghi báo cáo như một evaluation thành công. Có thể ghi failure artifact riêng, được đánh dấu rõ là failed.
9. Completion probability phải dùng sigmoid đúng một lần. Exercise prediction phải dùng logits/softmax đúng hợp đồng.
10. Macro metric phải dùng explicit class set được cấu hình. Trường hợp metric không xác định phải được báo rõ, không âm thầm thay bằng `0.0` nếu 0 có thể bị hiểu là kết quả hợp lệ.
11. Không được dùng test set để chọn epoch, threshold, model, hyperparameter hoặc checkpoint.

### H. Sửa và mở rộng unit test

Tất cả test phải dùng `tmp_path` hoặc cơ chế thư mục tạm tương đương. Test không được tạo thư mục hoặc file trong workspace artifact thật.

Bổ sung test tối thiểu cho các trường hợp sau:

1. Provenance phân loại mock là `MOCK` kể cả extraction status ghi success.
2. Extraction failure là `REJECTED`.
3. Quality gate fail là `REJECTED`/ineligible.
4. Thiếu source hoặc processed feature là ineligible.
5. Subject rỗng, `NaN`, sai định dạng hoặc ngoài tập dự kiến bị từ chối.
6. Exercise/label không hợp lệ bị từ chối, không bị ép âm thầm.
7. Provenance hash deterministic khi thứ tự record/dictionary thay đổi.
8. Trùng hoặc xung đột provenance mapping bị từ chối.
9. LOSO từ chối mock, rejected, candidate chưa verified và unknown record.
10. LOSO tạo đúng 10 fold; mỗi subject test đúng một lần.
11. Không giao nhau giữa train/validation/test theo subject, sample, source record và source-video group ở mọi fold.
12. LOSO từ chối thiếu/dư subject hoặc duplicate sample/source group.
13. Manifest row có đúng `fold_id` và `split`; output deterministic.
14. Normalization từ chối validation manifest.
15. Normalization từ chối test manifest.
16. Normalization từ chối train manifest chứa subject của validation/test.
17. Normalization từ chối wrong fold, wrong provenance hash, missing file, NaN/Inf và feature shape không đồng nhất.
18. Supervised Dataset từ chối row sai split, sai fold, ineligible, missing file, invalid label và legacy manifest.
19. Supervised Dataset từ chối augmentation khi split là validation/test.
20. SSL Dataset chấp nhận train-only manifest hợp lệ.
21. SSL Dataset từ chối manifest chứa dù chỉ một validation/test row.
22. SSL Dataset từ chối manifest thiếu split/fold hoặc sai normalization/provenance identity.
23. Train/pretrain entry point từ chối swapped manifest và wrong fold artifact.
24. Checkpoint contract nhất quán giữa save/load.
25. Evaluation thiếu checkpoint hoặc checkpoint metadata mismatch phải thất bại.
26. Evaluation không tạo success report khi model bắt buộc thất bại.
27. Completion logits được biến đổi bằng sigmoid đúng một lần.
28. Macro metrics dùng explicit class set; absent-class/undefined metric được biểu diễn rõ ràng.

Các test có thể được chia thành nhiều file. Tên test phải mô tả hành vi được bảo vệ.

## Trình tự thực hiện

1. Chụp trạng thái ban đầu bằng phương tiện read-only có sẵn. Nếu dự án không phải Git repository, ghi rõ rằng không thể dùng Git để chứng minh file không thay đổi; không được tuyên bố `git diff clean`.
2. Đọc code và lập bảng mapping từ từng acceptance criterion tới hàm và test chịu trách nhiệm.
3. Sửa provenance và eligibility API trước.
4. Sửa LOSO generator.
5. Sửa normalization.
6. Sửa supervised và SSL Dataset.
7. Sửa trainer/pretrainer/evaluator cùng checkpoint contract.
8. Viết test bằng fixture tạm.
9. Chạy **chỉ unit test Stage 2**. Không chạy lệnh nào truy cập hoặc xử lý 491 video thật.
10. Nếu test thất bại, sửa nguyên nhân rồi chạy lại đúng phạm vi test liên quan.
11. Kiểm tra không có artifact test bị để lại ngoài thư mục tạm.
12. Xuất báo cáo `PHASE_4_7_STAGE_2_CORRECTION_REPORT.md` ở thư mục gốc dự án.

## Lệnh được phép và không được phép

### Được phép

- Đọc/search mã nguồn và manifest.
- Kiểm tra schema hoặc tồn tại file bằng thao tác read-only.
- Chạy unit test Stage 2 dùng fixture tạm.
- Chạy syntax/type/static checks cục bộ nếu không kích hoạt pipeline dữ liệu.

### Không được phép

- Chạy `extract_keypoints.py` trên dataset thật.
- Chạy `process_features.py` trên dataset thật.
- Chạy `train.py`, `pretrain.py`, `train_loso.py` hoặc bất kỳ training job thật nào.
- Chạy evaluation/inference với checkpoint và test set thật.
- Xóa mock feature hoặc dữ liệu hiện có.
- Ghi vào `rehabai/data/interim`, `rehabai/data/processed`, `rehabai/training/checkpoints`, `rehabai/data/models/weights` hoặc thư mục metric/report kết quả thật, ngoại trừ file báo cáo correction được yêu cầu ở root.

## Điều kiện STOP ngay lập tức

Dừng và báo cáo thay vì tiếp tục nếu:

- Một unit test vô tình mở video thật hoặc khởi động extraction/training/evaluation.
- Một thay đổi có nguy cơ xóa hoặc ghi đè dữ liệu/checkpoint hiện có.
- Không thể xác định canonical identity giữa metadata, source video và processed feature.
- Test yêu cầu ghi artifact vào thư mục bảo vệ.
- Cần thay đổi định nghĩa nhãn hoặc danh sách subject nhưng chưa có bằng chứng nguồn.

## Tiêu chí PASS của Stage 2 Correction

Chỉ được ghi `PASS` khi đồng thời thỏa toàn bộ:

- Canonical provenance builder và deterministic manifest hash hoạt động.
- Eligibility gate được gọi thực sự từ LOSO, normalization, supervised Dataset và SSL Dataset.
- Không có đường gọi công khai nào có thể fit normalization bằng validation/test manifest.
- SSL từ chối mọi manifest không hoàn toàn train-only.
- Dataset từ chối wrong split, wrong fold, ineligible data và artifact identity mismatch.
- LOSO tạo đúng 10 fold và không có giao nhau theo subject/sample/source group.
- Checkpoint contract thống nhất giữa train và evaluation.
- Evaluation fail-closed khi thiếu/sai checkpoint.
- Toàn bộ test bắt buộc nêu trên tồn tại và pass.
- Test chỉ dùng fixture tạm và không để lại artifact trong thư mục dự án.
- Không có extraction, preprocessing, training hoặc evaluation thật được chạy.
- Không có dữ liệu hoặc checkpoint thật bị sửa/xóa.

Nếu còn bất kỳ mục nào chưa đạt, kết luận phải là `FAIL` hoặc `PARTIAL`, không được ghi `PASS`.

## Cấu trúc báo cáo bắt buộc

Tạo `PHASE_4_7_STAGE_2_CORRECTION_REPORT.md` gồm:

1. Executive conclusion: PASS/FAIL/PARTIAL.
2. Danh sách file đã đọc.
3. Danh sách file đã tạo/sửa.
4. Bảng từng lỗi reviewer và cách đã sửa.
5. Canonical provenance schema và quy tắc chuyển trạng thái.
6. Eligibility rules và nơi chúng được gọi.
7. LOSO invariants cùng bằng chứng test.
8. Normalization isolation invariants cùng bằng chứng test.
9. Supervised/SSL Dataset guards cùng bằng chứng test.
10. Checkpoint và evaluation fail-closed contract.
11. Danh sách toàn bộ test, hành vi mỗi test bảo vệ và kết quả.
12. Chính xác các command đã chạy.
13. Bằng chứng không chạy pipeline dữ liệu thật.
14. Bằng chứng unit test chỉ dùng thư mục tạm.
15. Các artifact hoặc thư mục ngoài ý muốn đã phát hiện và cách xử lý; không tự xóa dữ liệu cũ nếu chưa được yêu cầu.
16. Remaining risks/unknowns.
17. Stage 3 readiness: `READY` hoặc `NOT READY`, kèm lý do.
18. Compliance statement xác nhận không extraction, preprocessing, training, real evaluation hoặc data deletion.

## Yêu cầu cuối cùng dành cho Antigravity

Sau khi hoàn thành, hãy dừng hoàn toàn và chỉ trả về báo cáo. Không tự động chuyển sang Stage 3, không chạy dữ liệu thật và không khẳng định PASS nếu test chưa chứng minh đủ từng acceptance criterion.
