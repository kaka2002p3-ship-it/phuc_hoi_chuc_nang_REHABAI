# Ensemble decision

The ensemble combines RehabMotionNet upper-limb v2 and UpperLimbCTRGCN v1.
For each LOSO fold, the mixture weight was selected on that fold's validation
subject only; the test subject was evaluated once afterward.

| Model | Exercise Macro-F1 | Exercise accuracy |
|---|---:|---:|
| RehabMotionNet v2 | 0.3544 | 0.4379 |
| UpperLimbCTRGCN v1 | 0.3648 | 0.4335 |
| Validation-selected ensemble | **0.3744** | 0.4345 |

The ensemble is the strongest research candidate currently available, but the
fold standard deviation remains high (0.3319). It is therefore marked
experimental and is not a clinical correctness or error-type predictor.
Production promotion requires artifact export plus a fresh external subject
validation; the existing v2 artifact remains unchanged.
