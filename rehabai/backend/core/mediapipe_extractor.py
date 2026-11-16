"""Real-time MediaPipe-based pose and hand landmark extractor.

This module provides the RealtimeExtractor class that captures video frames,
extracts pose/hand landmarks using MediaPipe Holistic, and builds feature
vectors suitable for the ML inference pipeline.
"""
from __future__ import annotations

import cv2
import numpy as np
import mediapipe as mp
from collections import deque
from typing import Dict, Any, Optional, Tuple

from shared.preprocessing.normalization import normalize_landmarks
from shared.preprocessing.kinematics import get_kinematic_features

mp_holistic = mp.solutions.holistic


class PoseSmoother:
    """
    Exponential moving average smoother for pose landmarks.

    Reduces jitter in real-time tracking by blending current frame with
    previous smoothed values. Uses different smoothing factors for
    different body parts.
    """

    def __init__(
        self,
        alpha_pose: float = 0.3,
        alpha_hands: float = 0.4,
        min_valid_ratio: float = 0.5
    ):
        """
        Args:
            alpha_pose: Smoothing factor for pose landmarks (0=smooth, 1=no smooth)
            alpha_hands: Smoothing factor for hand landmarks
            min_valid_ratio: Minimum ratio of non-zero landmarks to apply smoothing
        """
        self.alpha_pose = alpha_pose
        self.alpha_hands = alpha_hands
        self.min_valid_ratio = min_valid_ratio
        self._prev_pose: Optional[np.ndarray] = None
        self._prev_lh: Optional[np.ndarray] = None
        self._prev_rh: Optional[np.ndarray] = None

    def _is_valid_landmark(self, arr: np.ndarray) -> bool:
        """Check if landmark has reasonable values (not all zeros)."""
        return np.abs(arr).sum() > 1e-6

    def _compute_valid_ratio(self, landmarks: np.ndarray) -> float:
        """Compute ratio of valid (non-zero) landmarks."""
        if landmarks.size == 0:
            return 0.0
        valid_count = np.sum(np.abs(landmarks).sum(axis=-1) > 1e-6)
        return valid_count / len(landmarks)

    def smooth(
        self,
        pose: np.ndarray,
        lh: np.ndarray,
        rh: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Apply temporal smoothing to landmarks.

        Args:
            pose: Pose landmarks, shape (33, 3)
            lh: Left hand landmarks, shape (21, 3)
            rh: Right hand landmarks, shape (21, 3)

        Returns:
            Smoothed (pose, lh, rh) tuple
        """
        # Determine if smoothing should be applied based on data quality
        pose_ratio = self._compute_valid_ratio(pose)
        lh_ratio = self._compute_valid_ratio(lh)
        rh_ratio = self._compute_valid_ratio(rh)

        # Adaptive smoothing based on quality
        pose_alpha = self.alpha_pose if pose_ratio >= self.min_valid_ratio else 1.0
        lh_alpha = self.alpha_hands if lh_ratio >= self.min_valid_ratio else 1.0
        rh_alpha = self.alpha_hands if rh_ratio >= self.min_valid_ratio else 1.0

        # Smooth pose
        if self._prev_pose is not None and pose_ratio >= self.min_valid_ratio:
            smoothed_pose = pose_alpha * pose + (1 - pose_alpha) * self._prev_pose
        else:
            smoothed_pose = pose.copy()
        self._prev_pose = smoothed_pose.copy()

        # Smooth left hand
        if self._prev_lh is not None and lh_ratio >= self.min_valid_ratio:
            smoothed_lh = lh_alpha * lh + (1 - lh_alpha) * self._prev_lh
        else:
            smoothed_lh = lh.copy()
        self._prev_lh = smoothed_lh.copy()

        # Smooth right hand
        if self._prev_rh is not None and rh_ratio >= self.min_valid_ratio:
            smoothed_rh = rh_alpha * rh + (1 - rh_alpha) * self._prev_rh
        else:
            smoothed_rh = rh.copy()
        self._prev_rh = smoothed_rh.copy()

        return smoothed_pose, smoothed_lh, smoothed_rh

    def reset(self):
        """Reset smoothing state."""
        self._prev_pose = None
        self._prev_lh = None
        self._prev_rh = None


class RealtimeExtractor:
    """
    Real-time pose and hand landmark extractor using MediaPipe Holistic.

    Captures video frames, extracts landmarks, applies temporal smoothing,
    buffers sequences, and builds feature vectors for ML inference.
    """

    def __init__(
        self,
        window_size: int = 96,
        stride: int = 5,
        enable_smoothing: bool = True,
        smoothing_alpha_pose: float = 0.3,
        smoothing_alpha_hands: float = 0.4
    ):
        """
        Args:
            window_size: Number of frames to buffer for feature extraction
            stride: Frames between consecutive feature extractions
            enable_smoothing: Whether to apply temporal smoothing
            smoothing_alpha_pose: Smoothing factor for pose landmarks
            smoothing_alpha_hands: Smoothing factor for hand landmarks
        """
        self.window_size = window_size
        self.stride = stride
        self.enable_smoothing = enable_smoothing

        # Smoothing (lazy import to avoid circular dependency)
        self._smoother: Optional[PoseSmoother] = None
        if enable_smoothing:
            self._smoother = PoseSmoother(
                alpha_pose=smoothing_alpha_pose,
                alpha_hands=smoothing_alpha_hands
            )

        # Frame buffers
        self.frames_processed_since_last_yield = 0
        self.pose_buffer = deque(maxlen=window_size)
        self.lh_buffer = deque(maxlen=window_size)
        self.rh_buffer = deque(maxlen=window_size)
        self.last_brightness = 0.0

        # Pre-initialize normalization stats (will be loaded on first use)
        self._kin_mean: Optional[np.ndarray] = None
        self._kin_std: Optional[np.ndarray] = None
        self._norm_loaded = False

        # MediaPipe model
        self.holistic = mp_holistic.Holistic(
            static_image_mode=False,
            model_complexity=1,  # Use 1 for real-time speed
            enable_segmentation=False,
            refine_face_landmarks=False
        )

    def _load_normalization_stats(self) -> None:
        """Lazy load normalization statistics from model loader."""
        if self._norm_loaded:
            return

        # Import here to avoid circular dependency at module level
        from backend.core.model_loader import model_loader
        self._kin_mean = model_loader.kin_mean
        self._kin_std = model_loader.kin_std
        self._norm_loaded = True

    def process_frame(self, image_rgb: np.ndarray) -> Optional[np.ndarray]:
        """
        Process a single video frame and extract landmarks.

        Args:
            image_rgb: RGB image array of shape (H, W, 3)

        Returns:
            Feature vector of shape (96, 237) if buffer is full and stride met,
            None otherwise.
        """
        # Compute brightness for quality monitoring
        self.last_brightness = float(
            cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY).mean()
        )

        # Extract landmarks with MediaPipe
        results = self.holistic.process(image_rgb)

        # Extract pose landmarks (x, y, z only, no visibility)
        if results.pose_landmarks:
            pose = np.array(
                [[lm.x, lm.y, lm.z] for lm in results.pose_landmarks.landmark],
                dtype=np.float32
            )
        else:
            pose = np.zeros((33, 3), dtype=np.float32)

        # Extract left hand landmarks
        if results.left_hand_landmarks:
            lh = np.array(
                [[lm.x, lm.y, lm.z] for lm in results.left_hand_landmarks.landmark],
                dtype=np.float32
            )
        else:
            lh = np.zeros((21, 3), dtype=np.float32)

        # Extract right hand landmarks
        if results.right_hand_landmarks:
            rh = np.array(
                [[lm.x, lm.y, lm.z] for lm in results.right_hand_landmarks.landmark],
                dtype=np.float32
            )
        else:
            rh = np.zeros((21, 3), dtype=np.float32)

        # Apply temporal smoothing if enabled
        if self._smoother is not None:
            pose, lh, rh = self._smoother.smooth(pose, lh, rh)

        # Add to buffers
        self.pose_buffer.append(pose)
        self.lh_buffer.append(lh)
        self.rh_buffer.append(rh)

        self.frames_processed_since_last_yield += 1

        # Yield feature vector when buffer is full and stride is met
        if (len(self.pose_buffer) == self.window_size and
                self.frames_processed_since_last_yield >= self.stride):
            self.frames_processed_since_last_yield = 0
            return self._build_feature_vector()

        return None

    def quality_status(
        self,
        exercise_id: Optional[int] = None,
        min_frames: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Return a conservative camera/landmark readiness signal for the UI.

        Args:
            exercise_id: Target exercise ID for specific quality checks
            min_frames: Minimum frames required before ready

        Returns:
            Dict with 'ready', 'code', 'message_vi', and quality metrics
        """
        if not self.pose_buffer:
            return {
                "ready": False,
                "code": "no_frames",
                "message_vi": "Đang chờ khung hình từ camera",
                "brightness": self.last_brightness
            }

        if self.last_brightness < 45.0:
            return {
                "ready": False,
                "code": "low_light",
                "message_vi": "Khung hình quá tối — hãy bật thêm đèn hoặc quay về phía nguồn sáng",
                "brightness": self.last_brightness
            }

        # Check specific landmarks based on exercise
        pose = np.asarray(self.pose_buffer)

        if exercise_id == 6:
            # Neck exercise: requires ears and shoulders
            frame_valid = np.any(
                np.abs(pose[:, [7, 8, 11, 12], :]) > 1e-6, axis=2
            ).all(axis=1)
            missing_message = "Chưa thấy rõ cả hai tai và hai vai — hãy ngồi đối diện camera"
        elif exercise_id == 4:
            # Hand exercise: requires at least one hand
            left = np.asarray(self.lh_buffer)
            right = np.asarray(self.rh_buffer)
            frame_valid = (
                np.any(np.abs(left) > 1e-6, axis=(1, 2)) |
                np.any(np.abs(right) > 1e-6, axis=(1, 2))
            )
            missing_message = "Chưa thấy bàn tay rõ — hãy đưa cả bàn tay vào khung hình"
        else:
            # Default: requires at least one arm (shoulder + elbow + wrist)
            left_arm = np.any(
                np.abs(pose[:, [11, 13, 15], :]) > 1e-6, axis=2
            ).all(axis=1)
            right_arm = np.any(
                np.abs(pose[:, [12, 14, 16], :]) > 1e-6, axis=2
            ).all(axis=1)
            frame_valid = left_arm | right_arm
            missing_message = "Chưa thấy đủ vai, khuỷu và cổ tay — hãy lùi xa và đưa tay vào khung hình"

        rate = float(frame_valid.mean())

        if rate < 0.60:
            return {
                "ready": False,
                "code": "insufficient_landmarks",
                "message_vi": missing_message,
                "landmark_rate": rate,
                "brightness": self.last_brightness
            }

        required_frames = self.window_size if min_frames is None else min_frames
        if len(self.pose_buffer) < required_frames:
            return {
                "ready": False,
                "code": "collecting_window",
                "message_vi": f"Đang kiểm tra độ ổn định ({len(self.pose_buffer)}/{required_frames} khung)",
                "landmark_rate": rate,
                "brightness": self.last_brightness
            }

        return {
            "ready": True,
            "code": "ready",
            "message_vi": "Đã thấy đủ tay để phân tích",
            "landmark_rate": rate,
            "brightness": self.last_brightness
        }

    def _build_feature_vector(self) -> np.ndarray:
        """
        Build feature vector from buffered landmarks.

        Returns:
            Feature vector of shape (96, 237) with:
            - 99 pose features (33 landmarks * 3 coords)
            - 63 left hand features (21 landmarks * 3 coords)
            - 63 right hand features (21 landmarks * 3 coords)
            - 12 kinematic features (angles + velocities)
        """
        # Get buffered landmarks
        pose_arr = np.array(self.pose_buffer)  # (96, 33, 3)
        lh_arr = np.array(self.lh_buffer)      # (96, 21, 3)
        rh_arr = np.array(self.rh_buffer)       # (96, 21, 3)

        # 1. Normalize coordinates (shoulder centering + scaling)
        norm_pose, norm_lh, norm_rh = normalize_landmarks(pose_arr, lh_arr, rh_arr)

        # 2. Extract kinematic features
        kinematics = get_kinematic_features(norm_pose, fps=30.0)  # (96, 12)

        # 3. Standardize kinematics using model normalization stats
        self._load_normalization_stats()
        if self._kin_mean is not None and self._kin_std is not None:
            kinematics = (kinematics - self._kin_mean) / self._kin_std

        # 4. Flatten landmarks
        pose_flat = norm_pose.reshape(self.window_size, -1)   # (96, 99)
        lh_flat = norm_lh.reshape(self.window_size, -1)       # (96, 63)
        rh_flat = norm_rh.reshape(self.window_size, -1)       # (96, 63)

        # 5. Concatenate all features
        features = np.concatenate(
            [pose_flat, lh_flat, rh_flat, kinematics], axis=1
        )  # (96, 237)

        return features

    def get_skeleton(self) -> Optional[Dict[str, list]]:
        """
        Get latest raw landmarks for skeleton overlay.

        Returns:
            Dict with 'pose', 'left_hand', 'right_hand' keys,
            or None if no frames captured yet.
        """
        if len(self.pose_buffer) == 0:
            return None
        return {
            "pose": self.pose_buffer[-1].tolist(),
            "left_hand": self.lh_buffer[-1].tolist(),
            "right_hand": self.rh_buffer[-1].tolist()
        }

    def reset(self) -> None:
        """Reset all buffers and internal state."""
        self.pose_buffer.clear()
        self.lh_buffer.clear()
        self.rh_buffer.clear()
        self.frames_processed_since_last_yield = 0
        self.last_brightness = 0.0
        if self._smoother is not None:
            self._smoother.reset()
