# Datanew expert video-group split

- Group key: `video_id`; no video appears in more than one split.
- Only expert-confirmed `correct/incorrect` labels are included.
- `uncertain` rows are excluded.

## Split summary
- ELBOW_FLEXION / train: rows=268, videos=35, correct=254, incorrect=14
- ELBOW_FLEXION / val: rows=56, videos=8, correct=54, incorrect=2
- ELBOW_FLEXION / test: rows=58, videos=8, correct=57, incorrect=1
- HAND_OPENING / train: rows=358, videos=89, correct=354, incorrect=4
- HAND_OPENING / val: rows=86, videos=19, correct=86, incorrect=0
- HAND_OPENING / test: rows=75, videos=19, correct=75, incorrect=0

## Warnings
- HAND_OPENING: only 1 video(s) contain incorrect labels; val/test may be single-class or empty for incorrect. Do not report binary generalization F1.