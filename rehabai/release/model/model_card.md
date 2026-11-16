# RehabMotionNet upper-limb v2 model card

## Dataset and task
- Dataset: Upper Limb Stroke, 491 source videos; 387 samples passed the
  upper-limb quality gate.
- Task: four-class exercise recognition. Completion status is reported only
  as an experimental auxiliary head and is not promoted to production.
- Split: strict subject-wise 10-fold LOSO; normalization fitted on each
  training partition only.

## Results
- Exercise Macro-F1: 0.3544 +/- 0.2704
- Exercise accuracy: 0.4379 +/- 0.2335
- Completion Macro-F1: 0.4828 (experimental)

## Runtime contract
- Architecture signature: `rehab_motionnet_upper_limb_v2`
- Input: 96 frames x 237 float32 features
- Upper-limb pose nodes: shoulder, elbow and wrist joints (6 pose nodes)
- Registry SHA-256: `15aed6590bd590dee2e45273ec2ddaa63b992c0fc056e5c1aca1fd83b99f5d72`

## Limitations and intended use
This is a research/demo inference model. It must not be used as a medical
diagnosis, and it does not replace a qualified healthcare professional.
Error-type feedback and clinical correctness claims are disabled because no
verified expert-labelled extension dataset is available.
