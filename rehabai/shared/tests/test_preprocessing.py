import numpy as np
from shared.preprocessing.normalization import get_body_center, get_shoulder_width, normalize_landmarks
from shared.preprocessing.kinematics import get_kinematic_features, calculate_angle
from shared.preprocessing.sequence import resample_sequence

def test_normalization():
    # Mock pose data (N, 33, 3)
    pose = np.zeros((1, 33, 3))
    
    # Left shoulder at (-1, 1, 0), Right shoulder at (1, 1, 0)
    # Center should be (0, 1, 0)
    pose[0, 11] = [-1, 1, 0]
    pose[0, 12] = [1, 1, 0]
    
    center = get_body_center(pose)
    assert np.allclose(center, [[0, 1, 0]])
    
    scale = get_shoulder_width(pose)
    assert np.allclose(scale, [2.0])
    
    # Mock hand data
    lh = np.zeros((1, 21, 3))
    rh = np.zeros((1, 21, 3))
    
    norm_pose, norm_lh, norm_rh = normalize_landmarks(pose, lh, rh)
    
    # Check if center is moved to 0,0,0
    assert np.allclose(norm_pose[0, 11], [-0.5, 0, 0])
    assert np.allclose(norm_pose[0, 12], [0.5, 0, 0])
    
def test_calculate_angle():
    v1 = np.array([[1, 0, 0]])
    v2 = np.array([[0, 1, 0]])
    angle = calculate_angle(v1, v2)
    assert np.allclose(angle, [np.pi / 2])
    
def test_kinematics():
    # Mock pose for a T-pose
    pose = np.zeros((2, 33, 3))
    
    # Frame 0
    pose[0, 11] = [-1, 1, 0] # L shoulder
    pose[0, 12] = [1, 1, 0]  # R shoulder
    pose[0, 13] = [-2, 1, 0] # L elbow
    pose[0, 14] = [2, 1, 0]  # R elbow
    pose[0, 15] = [-3, 1, 0] # L wrist
    pose[0, 16] = [3, 1, 0]  # R wrist
    pose[0, 23] = [-0.5, -1, 0] # L hip
    pose[0, 24] = [0.5, -1, 0]  # R hip
    
    # Frame 1: move wrist down 1 unit
    pose[1] = pose[0].copy()
    pose[1, 15] = [-3, 0, 0]
    
    features = get_kinematic_features(pose, fps=30.0)
    
    assert features.shape == (2, 12)
    # L_wrist velocity for frame 1: distance = 1, dt = 1/30, so vel = 30
    assert np.isclose(features[1, 10], 30.0)
    
def test_resample():
    seq = np.array([[0, 0], [10, 10], [20, 20]]) # 3 frames
    resampled = resample_sequence(seq, target_length=5)
    
    assert resampled.shape == (5, 2)
    assert np.allclose(resampled[0], [0, 0])
    assert np.allclose(resampled[2], [10, 10])
    assert np.allclose(resampled[4], [20, 20])

if __name__ == "__main__":
    test_normalization()
    test_calculate_angle()
    test_kinematics()
    test_resample()
    print("All preprocessing tests passed!")
