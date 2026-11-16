# Datanew automatic pipeline audit

## Scope
- Labels are `auto_rule_v1`: quartiles of signal range, not expert or clinical ground truth.
- Metrics are therefore pipeline smoke-test results only.

## Label counts
- ELBOW_FLEXION / correct: 101
- ELBOW_FLEXION / incorrect: 101
- HAND_OPENING / correct: 130
- HAND_OPENING / incorrect: 130

## Source groups
- ELBOW_FLEXION / ex1: 66 reviewed rows
- ELBOW_FLEXION / ex2: 85 reviewed rows
- ELBOW_FLEXION / ex3: 51 reviewed rows
- HAND_OPENING / ex1: 48 reviewed rows
- HAND_OPENING / ex2: 181 reviewed rows
- HAND_OPENING / ex3: 31 reviewed rows

## No-leakage smoke test
- ELBOW_FLEXION: F1=1.0000, accuracy=1.0000
- HAND_OPENING: F1=1.0000, accuracy=1.0000

The first "no-leakage" run removed `signal_range`, but retained `signal_min`,
`signal_max`, and `signal_std`; these remain strong proxies for the quartile
labeling rule. It must therefore still be treated as leakage-contaminated.

## Strict proxy-removal smoke test

Only segment start/end times were retained; all signal amplitude/statistical
features were removed.

- ELBOW_FLEXION: F1=0.7018, accuracy=0.7027 (37 test reps from 13 held-out videos).
- HAND_OPENING: F1=0.7723, accuracy=0.8065 (62 test reps from 26 held-out videos).

These scores measure correlation with heuristic labels and video timing. They
still do not measure clinical correctness.

## Interpretation
- The apparent perfect score is expected because auto_rule_v1 defines the target from signal range and related extrema features remain in the input.
- This is not evidence of correctness recognition.
- Required next valid evidence: expert-reviewed labels and a predeclared subject-wise split with the labeling rule excluded from features.
