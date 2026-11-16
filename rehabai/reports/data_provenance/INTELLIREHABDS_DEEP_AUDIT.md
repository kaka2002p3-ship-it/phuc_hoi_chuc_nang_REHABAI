# IntelliRehabDS deep audit

This is a read-only auxiliary-data audit. No source gesture is mapped to
the immutable RehabAI product registry and no product training manifest is created.

- Status: `FAIL_SEQUENCE_VALIDATION`
- Sequences: 2589 raw; 2589 simplified; valid=2544
- Subjects identified from source filenames: 30
- Gestures (source ontology): {'0': 258, '1': 279, '2': 376, '3': 318, '4': 277, '5': 257, '6': 260, '7': 274, '8': 290}
- Correctness labels (source ontology): {'1': 2047, '2': 530, '3': 12}
- Frame count range: 13–4736 (mean 88.18)
- Joint schema: 25 Kinect joints × XYZ (75 values/frame)

## Recommended next experiment

Use IntelliRehabDS only for a predeclared self-supervised motion encoder
or source-correctness auxiliary task. Keep all product subjects and labels
isolated, fit normalization within each training partition, and evaluate
the frozen encoder on the existing strict LOSO folds without architecture
selection on their test results.
