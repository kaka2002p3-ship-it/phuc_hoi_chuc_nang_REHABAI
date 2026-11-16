import numpy as np

# Landmark indices
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24

def calculate_angle(v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
    """
    Calculate the angle in radians between two sets of vectors.
    v1, v2: shape (N, 3)
    Returns: angle in radians, shape (N,)
    """
    # Normalize vectors
    v1_u = v1 / (np.linalg.norm(v1, axis=1, keepdims=True) + 1e-6)
    v2_u = v2 / (np.linalg.norm(v2, axis=1, keepdims=True) + 1e-6)
    
    # Dot product
    dot_product = np.sum(v1_u * v2_u, axis=1)
    # Clip to avoid numerical errors with arccos
    dot_product = np.clip(dot_product, -1.0, 1.0)
    
    return np.arccos(dot_product)

def get_kinematic_features(pose_landmarks: np.ndarray, fps: float = 30.0) -> np.ndarray:
    """
    Extract kinematic features from pose sequence.
    pose_landmarks: shape (N, 33, 3)
    Returns: features array of shape (N, num_features)
    """
    N = pose_landmarks.shape[0]
    dt = 1.0 / fps
    
    features = []
    
    # 1. Angles
    # Left Shoulder Angle (Hip -> Shoulder -> Elbow)
    l_trunk = pose_landmarks[:, L_SHOULDER, :3] - pose_landmarks[:, L_HIP, :3]
    l_arm = pose_landmarks[:, L_ELBOW, :3] - pose_landmarks[:, L_SHOULDER, :3]
    l_shoulder_angle = calculate_angle(l_trunk, l_arm)
    
    # Right Shoulder Angle
    r_trunk = pose_landmarks[:, R_SHOULDER, :3] - pose_landmarks[:, R_HIP, :3]
    r_arm = pose_landmarks[:, R_ELBOW, :3] - pose_landmarks[:, R_SHOULDER, :3]
    r_shoulder_angle = calculate_angle(r_trunk, r_arm)
    
    # Left Elbow Angle (Shoulder -> Elbow -> Wrist)
    l_forearm = pose_landmarks[:, L_WRIST, :3] - pose_landmarks[:, L_ELBOW, :3]
    l_elbow_angle = calculate_angle(-l_arm, l_forearm)
    
    # Right Elbow Angle
    r_forearm = pose_landmarks[:, R_WRIST, :3] - pose_landmarks[:, R_ELBOW, :3]
    r_elbow_angle = calculate_angle(-r_arm, r_forearm)
    
    # Trunk Inclination (Mid-Hip to Mid-Shoulder vs Vertical)
    mid_hip = (pose_landmarks[:, L_HIP, :3] + pose_landmarks[:, R_HIP, :3]) / 2.0
    mid_shoulder = (pose_landmarks[:, L_SHOULDER, :3] + pose_landmarks[:, R_SHOULDER, :3]) / 2.0
    spine = mid_shoulder - mid_hip
    vertical = np.zeros_like(spine)
    vertical[:, 1] = -1.0 # y-axis points down in image space, so up is negative y
    trunk_inclination = calculate_angle(spine, vertical)
    
    angles = np.stack([
        l_shoulder_angle, r_shoulder_angle,
        l_elbow_angle, r_elbow_angle,
        trunk_inclination
    ], axis=1) # (N, 5)
    
    features.append(angles)
    
    # 2. Angular Velocity (Derivative of angles)
    angular_velocity = np.zeros_like(angles)
    angular_velocity[1:] = (angles[1:] - angles[:-1]) / dt
    # Copy first frame to avoid zero at start
    angular_velocity[0] = angular_velocity[1] if N > 1 else 0
    features.append(angular_velocity)
    
    # 3. Velocity of wrists (scalar magnitude)
    l_wrist_vel = np.zeros(N)
    r_wrist_vel = np.zeros(N)
    
    l_wrist_pos = pose_landmarks[:, L_WRIST, :3]
    r_wrist_pos = pose_landmarks[:, R_WRIST, :3]
    
    l_wrist_vel[1:] = np.linalg.norm(l_wrist_pos[1:] - l_wrist_pos[:-1], axis=1) / dt
    r_wrist_vel[1:] = np.linalg.norm(r_wrist_pos[1:] - r_wrist_pos[:-1], axis=1) / dt
    
    l_wrist_vel[0] = l_wrist_vel[1] if N > 1 else 0
    r_wrist_vel[0] = r_wrist_vel[1] if N > 1 else 0
    
    velocities = np.stack([l_wrist_vel, r_wrist_vel], axis=1) # (N, 2)
    features.append(velocities)
    
    # Concatenate all features
    kinematics = np.concatenate(features, axis=1) # (N, 5 + 5 + 2) = (N, 12)
    return kinematics
