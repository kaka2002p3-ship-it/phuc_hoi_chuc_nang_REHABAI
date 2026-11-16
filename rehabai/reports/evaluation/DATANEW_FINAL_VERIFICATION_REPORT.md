# Datanew — Final Verification Report

**Ngày kiểm tra:** 2026-09-18  
**Phạm vi:** extraction → self-supervised pretraining → 10-fold subject-wise LOSO → artifact audit  
**Trạng thái:** **RESEARCH PASS / PRODUCTION FAIL**

## 1. Kết luận điều hành

Pipeline đã chạy hoàn chỉnh và artifact có thể tái nạp được. Không phát hiện file feature bị thiếu, NaN/Inf, trùng hash, sai schema, sai fold hoặc sai provenance. Tuy nhiên candidate chưa đủ bằng chứng để thay thế model production: kết quả được tạo bằng một seed, chỉ có 10 fold, độ biến thiên giữa subject rất lớn, có các fold exercise đạt 0%, và môi trường PyTorch/CUDA không đúng profile canonical.

**Quyết định:** giữ nguyên model production hiện tại; không promote `datanew_ssl_all_full`.

Completion có tín hiệu tốt hơn baseline và có thể giữ làm **research candidate**, nhưng chưa được gọi là model sản xuất/clinical-ready. Không có bước reinforcement learning (RL) trong pipeline này; đây là self-supervised pretraining và supervised fine-tuning.

## 2. Inventory và chất lượng dữ liệu

| Nguồn | Ready | Loại | Ghi chú |
|---|---:|---:|---|
| AVI archives | 200 | 0 | — |
| EHWGesture RGB | 240 | 0 | — |
| ex1 | 36 | 40 | 38 quá ngắn, 2 pose missing cao |
| ex2 | 114 | 0 | — |
| ex3 | 29 | 19 | pose missing cao |
| **Tổng unique** | **619** | **59** | quality gate đã áp dụng |

Manifest kiểm tra: `data/datanew_unlabeled/combined_ready_manifest.csv`.

- 619/619 record có `status=ready`.
- 619/619 output `.npz` tồn tại.
- 619/619 có cùng schema: 96 frame; pose `(96,33,3)`, hai tay `(96,21,3)`, kinematics `(96,12)`.
- Không có NaN/Inf.
- Không có duplicate file, output path hoặc SHA-256 nội dung.
- Hash manifest: `2d5c5fa206f555cc95bb53598b784c3040f1686c31089ad824dd4a01ea53ec1e`.

## 3. Integrity của artifact

### Encoder SSL

Artifact: `experiments/datanew_ssl_all/datanew_ssl_all_encoder.pth`

- Load thành công bằng `torch.load(..., weights_only=True)`.
- `architecture_signature=datanew_ssl_encoder_v1`.
- `input_contract=common_upper_limb_237_v1`.
- `sample_count=619`, `seed=42`.
- `ontology_mapping_to_product=null` — không ép nhãn ngoài vào ontology sản phẩm.
- SHA-256 artifact: `30a10eeb8a17ce47ebd7ce096d61ee0dc9727cedb7f1148b5f82da71759af49c`.
- Loss SSL tốt nhất: `0.0252295452` sau 50 epoch; history hữu hạn.

### 10 checkpoint supervised

- Đủ các fold `fold_01` đến `fold_10`; mỗi fold có đúng một checkpoint `RehabMotionNet_*_supervised_model.pth`.
- Tất cả load được với `weights_only=True`.
- `fold_id`, protocol `1.1`, architecture, role, train-manifest hash, normalization hash và provenance hash khớp metadata canonical của fold.
- Nested `training_inputs.external_encoder.artifact_sha256` khớp encoder SSL; manifest hash external khớp manifest hiện tại; ontology mapping vẫn là `null`.
- 10/10 training summary đọc được; history, loss/F1 và best epoch đều hữu hạn. Một số fold có cảnh báo overfitting, được ghi nhận trong summary.

## 4. Protocol đánh giá

- Strict subject-wise 10-fold LOSO.
- Tổng test samples: **387**; completion cũng **387**.
- Test manifest không bị thay đổi trong lần chạy xác minh.
- Lệnh evaluate chạy lại thành công và tạo cùng byte output (SHA-256 trước/sau giống nhau).
- Không sửa production artifact.
- Runtime thực tế: Python 3.11.9, `torch 2.5.1+cu121`, RTX 4060 Laptop; đây là `noncanonical_exploratory`, không phải profile canonical `torch 2.7.0+cu126`.

## 5. Kết quả LOSO mới nhất

Các số dưới đây lấy trực tiếp từ `datanew_ssl_all_full_loso.json`; giá trị là trung bình 10 fold (macro theo fold). `delta` là candidate trừ baseline v2.

| Metric | Baseline v2 | Datanew combined | Delta |
|---|---:|---:|---:|
| Exercise Macro-F1 | 0.3544 | 0.3718 | **+0.0174** |
| Exercise accuracy | 0.4379 | 0.4646 | **+0.0266** |
| Completion Macro-F1 | 0.4828 | 0.5606 | **+0.0778** |
| Completion accuracy | 0.5024 | 0.5803 | **+0.0779** |

Độ lệch chuẩn candidate giữa fold:

- Exercise accuracy: `0.2838`.
- Exercise Macro-F1: `0.2870`.
- Completion accuracy: `0.1013`.
- Completion Macro-F1: `0.1077`.

Số fold thắng/hòa/thua so với baseline:

| Metric | Thắng | Hòa | Thua |
|---|---:|---:|---:|
| Exercise accuracy | 4 | 1 | 5 |
| Exercise Macro-F1 | 4 | 0 | 6 |
| Completion accuracy | 5 | 2 | 3 |
| Completion Macro-F1 | 5 | 1 | 4 |

Confusion matrix aggregate exercise:

```text
[[72, 13, 13, 25],
 [23, 42,  0,  0],
 [15,  1, 63, 25],
 [23,  9, 25, 38]]
```

Confusion matrix aggregate completion:

```text
[[99, 101],
 [66, 121]]
```

Lưu ý quan trọng: chỉ **4/10 fold** có đủ cả 4 exercise class trong test; các subject còn lại vốn có coverage không đầy đủ. Fold 07 và 08 đạt exercise accuracy/F1 bằng `0.0`, nên mean cải thiện không đủ để kết luận generalization đã ổn định.

## 6. PASS/FAIL gates

| Gate | Kết quả | Đánh giá |
|---|---|---|
| Extraction hoàn tất, raw data không bị sửa | PASS | 619 ready |
| Feature integrity/schema/finiteness | PASS | 619/619 hợp lệ |
| Encoder metadata và manifest hash | PASS | khớp |
| Đủ 10 checkpoint và summary | PASS | 10/10 |
| Provenance/normalization/train hash | PASS | 10/10 |
| Reproducible evaluate | PASS | output hash không đổi |
| Exercise cải thiện có tính ổn định | **FAIL** | variance rất cao, 5/10 fold thua accuracy và 6/10 thua Macro-F1 |
| Completion đủ bằng chứng promotion | **FAIL** | một seed, power 10 fold thấp, chưa có fresh-subject/multi-seed |
| Canonical runtime | **FAIL** | torch/CUDA không đúng profile |
| Production/clinical readiness | **FAIL** | chưa có prospective/fresh-subject validation |

## 7. So sánh với các candidate trước

- AVI-only SSL + full model: exercise Macro-F1 `0.3575`, completion Macro-F1 `0.4900`.
- Combined 619-video SSL + full model: exercise Macro-F1 `0.3718`, completion Macro-F1 `0.5606` theo JSON đánh giá hiện tại.
- AVI-only frozen adapter: completion cao hơn nhưng exercise recognition giảm mạnh; không phù hợp làm model chung.

`DATANEW_AUTOMATED_TRAINING_REPORT.md` là báo cáo sơ bộ cũ và chứa số liệu candidate khác với JSON mới nhất. Báo cáo này ưu tiên JSON được sinh lại lúc xác minh (`datanew_ssl_all_full_loso.json`) làm nguồn sự thật.

## 8. Việc cần làm trước khi cân nhắc promote

1. Chạy lại combined SSL/fine-tuning tối thiểu 3–5 seed trong đúng canonical environment.
2. Giữ nguyên test subjects; dùng validation chỉ để chọn hyperparameter, không chọn theo test.
3. Thu thập fresh subjects/prospective set và đánh giá riêng exercise/completion.
4. Đặt gate riêng: exercise không được giảm so với production; completion phải vượt baseline với khoảng tin cậy và calibration đạt yêu cầu.
5. Điều tra fold 07–10 và class imbalance trước khi tăng model size.
6. Chỉ sau khi các gate trên đạt mới tạo release artifact; hiện tại không copy checkpoint vào `release/model`.

## 9. Lệnh tái kiểm tra

```powershell
cd D:\PhucHoiChucNangTay\rehabai
python -m py_compile scripts\extract_datanew.py scripts\prepare_datanew_unlabeled.py training\pretrain_datanew_ssl.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_datanew_experiment.ps1 -Stage evaluate
```

**Kết luận cuối:** pipeline và artifact đạt yêu cầu nghiên cứu, nhưng mô hình chưa đạt yêu cầu phát hành production. Giữ model hiện tại trong production và lưu candidate datanew ở phạm vi research-only.
