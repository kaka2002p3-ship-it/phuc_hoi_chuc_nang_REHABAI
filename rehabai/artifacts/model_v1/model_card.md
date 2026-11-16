# Model Card: RehabMotionNet v1.0

## 1. Dataset
- Source: Upper Limb Stroke (Subset verified in Phase 1) + MobiPhysio + REHAB24-6.
- Split Rule: Subject-wise to prevent data leakage.
- Total samples evaluated: 11 (representative).

## 2. Task
- Multi-task learning:
  1. Exercise Classification (4 canonical exercises).
  2. Completion Score Regression.

## 3. Label Semantics
- Canonical IDs: 1 (Vai), 2 (Khuỷu tay), 3 (Cổ tay), 4 (Ngón tay).
- Score: Continuous [0.0, 100.0] or equivalent mapping.

## 4. Metrics
- Accuracy: 1.0
- Macro F1: 1.0
- Completion RMSE: 0.8168041110038757
- Latency (ms): 8.439437000001817

## 5. Limitations
- Error type classification is **DISABLED** (Phase 10 skipped due to lack of verified clinical data).
- The model relies heavily on consistent viewpoint extraction via MediaPipe Holistic.

## 6. Intended Use
- Use for offline analysis and realtime inference in RehabAI application.
- **DISCLAIMER: KHÔNG THAY THẾ CHUYÊN GIA Y TẾ. Mọi đánh giá chỉ mang tính chất tham khảo.**

## 7. Registry Version
- Hash (SHA-256): 15aed6590bd590dee2e45273ec2ddaa63b992c0fc056e5c1aca1fd83b99f5d72
