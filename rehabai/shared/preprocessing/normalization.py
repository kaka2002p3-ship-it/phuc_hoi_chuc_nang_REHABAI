import numpy as np

# MediaPipe Pose Landmark Indices
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12

def get_body_center(pose_landmarks: np.ndarray) -> np.ndarray:
    """
    Calculate the body center based on the mid-point of the shoulders.
    pose_landmarks: shape (N, 33, 3) or (33, 3)
    Returns: center coordinates of shape (N, 3) or (3,)
    """
    if pose_landmarks.ndim == 3:
        left_shoulder = pose_landmarks[:, LEFT_SHOULDER, :3]
        right_shoulder = pose_landmarks[:, RIGHT_SHOULDER, :3]
    else:
        left_shoulder = pose_landmarks[LEFT_SHOULDER, :3]
        right_shoulder = pose_landmarks[RIGHT_SHOULDER, :3]
        
    center = (left_shoulder + right_shoulder) / 2.0
    return center

def get_shoulder_width(pose_landmarks: np.ndarray) -> np.ndarray:
    """
    Calculate the distance between left and right shoulders to use as a scale factor.
    pose_landmarks: shape (N, 33, 3) or (33, 3)
    Returns: scale of shape (N,) or scalar
    """
    if pose_landmarks.ndim == 3:
        left_shoulder = pose_landmarks[:, LEFT_SHOULDER, :3]
        right_shoulder = pose_landmarks[:, RIGHT_SHOULDER, :3]
        scale = np.linalg.norm(left_shoulder - right_shoulder, axis=1)
    else:
        left_shoulder = pose_landmarks[LEFT_SHOULDER, :3]
        right_shoulder = pose_landmarks[RIGHT_SHOULDER, :3]
        scale = np.linalg.norm(left_shoulder - right_shoulder)
        
    # Prevent division by zero
    scale = np.where(scale < 1e-5, 1.0, scale)
    return scale

def normalize_translation(landmarks: np.ndarray, center: np.ndarray) -> np.ndarray:
    """
    Translate landmarks so that the center is at (0,0,0).
    landmarks: shape (N, V, 3) or (N, V, 4) or (V, 3) or (V, 4)
    center: shape (N, 3) or (3,)
    """
    res = landmarks.copy()
    if landmarks.ndim == 3:
        res[..., :3] = landmarks[..., :3] - center[:, np.newaxis, :]
    else:
        res[..., :3] = landmarks[..., :3] - center[np.newaxis, :]
    return res

def normalize_scale(landmarks: np.ndarray, scale: np.ndarray) -> np.ndarray:
    """
    Scale landmarks by a given scale factor.
    landmarks: shape (N, V, 3) or (N, V, 4) or (V, 3) or (V, 4)
    scale: shape (N,) or scalar
    """
    res = landmarks.copy()
    if landmarks.ndim == 3:
        res[..., :3] = landmarks[..., :3] / scale[:, np.newaxis, np.newaxis]
    else:
        res[..., :3] = landmarks[..., :3] / scale
    return res

def normalize_landmarks(pose: np.ndarray, left_hand: np.ndarray, right_hand: np.ndarray):
    """
    Normalize all landmark streams using the pose center and scale.
    """
    center = get_body_center(pose)
    scale = get_shoulder_width(pose)
    
    norm_pose = normalize_scale(normalize_translation(pose, center), scale)
    norm_lh = normalize_scale(normalize_translation(left_hand, center), scale)
    norm_rh = normalize_scale(normalize_translation(right_hand, center), scale)
    
    return norm_pose, norm_lh, norm_rh
