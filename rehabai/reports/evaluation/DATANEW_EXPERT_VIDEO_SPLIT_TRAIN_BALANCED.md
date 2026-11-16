# Expert-label balanced training manifest

- Only expert-confirmed `correct/incorrect` rows are included.
- All `incorrect` rows are retained.
- `correct` rows are sampled without replacement; no synthetic labels or duplicate rows are created.
- This file is for training only; it is not a valid subject-wise test split.

## Summary
- ELBOW_FLEXION: incorrect=14, correct=14, total=28, incorrect_videos=2
- HAND_OPENING: incorrect=4, correct=4, total=8, incorrect_videos=1

## Critical limitation
- HAND_OPENING has only one video containing incorrect reps. A video-disjoint test set cannot contain both classes until more incorrect videos are labeled.
- ELBOW_FLEXION has incorrect reps in four videos, all from source ex1; source groups are not confirmed subjects.