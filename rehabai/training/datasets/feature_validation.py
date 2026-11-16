from typing import Mapping, Any
import numpy as np

FEATURE_SHAPES = {
    "pose_landmarks": (33, 4),
    "left_hand_landmarks": (21, 3),
    "right_hand_landmarks": (21, 3),
}
KINEMATICS_DIM = 12


def validate_feature_arrays(
    data: Mapping[str, Any],
    file_path: str,
    expected_kinematics_dim: int = KINEMATICS_DIM,
) -> None:
    """Validate the persisted Phase 4.7 feature contract before a sample is accepted."""
    if expected_kinematics_dim != KINEMATICS_DIM:
        raise ValueError(
            f"Normalization feature_dimension must be {KINEMATICS_DIM}, got {expected_kinematics_dim}"
        )

    expected = {"kinematics": (expected_kinematics_dim,), **FEATURE_SHAPES}
    frame_count = None
    for key, trailing_shape in expected.items():
        if key not in data:
            raise KeyError(f"Feature missing {key} in {file_path}")
        value = data[key]
        if not isinstance(value, np.ndarray):
            raise TypeError(f"{key} is not a numpy array in {file_path}")
        if value.dtype.kind not in "iuf":
            raise TypeError(f"{key} must contain real numeric values in {file_path}; got {value.dtype}")
        required_ndim = len(trailing_shape) + 1
        if value.ndim != required_ndim or tuple(value.shape[1:]) != trailing_shape:
            expected_text = ", ".join(map(str, trailing_shape))
            raise ValueError(
                f"Invalid {key} shape in {file_path}: expected (T, {expected_text}), got {value.shape}"
            )
        if value.shape[0] <= 0:
            raise ValueError(f"Empty sequence for {key} in {file_path}")
        if not np.isfinite(value).all():
            raise ValueError(f"NaN or Inf {key} detected in {file_path}")
        if frame_count is None:
            frame_count = value.shape[0]
        elif value.shape[0] != frame_count:
            raise ValueError(f"Frame count mismatch across modalities in {file_path}")
