import numpy as np
from scipy.interpolate import interp1d

def resample_sequence(sequence: np.ndarray, target_length: int) -> np.ndarray:
    """
    Resample a sequence to a target length using linear interpolation.
    sequence: shape (N, D1, D2, ...) where N is the number of frames.
    target_length: The desired number of frames.
    """
    N = sequence.shape[0]
    if N == target_length:
        return sequence
        
    if N == 1:
        # If only 1 frame, just repeat it
        return np.repeat(sequence, target_length, axis=0)
        
    # Original time points
    t_orig = np.linspace(0, 1, N)
    # Target time points
    t_target = np.linspace(0, 1, target_length)
    
    # Flatten spatial dimensions for interpolation
    shape = sequence.shape
    flattened = sequence.reshape(N, -1)
    
    # Interpolate along axis 0
    f = interp1d(t_orig, flattened, axis=0, kind='linear', assume_sorted=True)
    resampled_flattened = f(t_target)
    
    # Restore original spatial shape
    target_shape = (target_length,) + shape[1:]
    return resampled_flattened.reshape(target_shape)

def temporal_scaling(sequence: np.ndarray, scale_range: tuple = (0.8, 1.2)) -> np.ndarray:
    """
    Data augmentation: speed up or slow down the sequence by a random factor, 
    then resample back to original length.
    """
    N = sequence.shape[0]
    scale = np.random.uniform(scale_range[0], scale_range[1])
    temp_length = max(2, int(N * scale))
    
    # Stretch/compress
    scaled_seq = resample_sequence(sequence, temp_length)
    
    # Resample back to original N (or just return the scaled one to let collate_fn pad/resample it)
    # Here we resample back to N to keep shape consistent in the pipeline if we want fixed N early on.
    # However, standard temporal scaling might crop or pad. 
    # Let's resample back to N to maintain simple batching, which simulates performing the action faster/slower.
    return resample_sequence(scaled_seq, N)
