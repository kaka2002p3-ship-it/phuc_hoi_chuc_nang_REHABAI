"""
Advanced data augmentation for motion sequences.

All augmentations preserve exercise label semantics:
- Temporal scaling preserves which exercise was performed
- Noise/masking simulates realistic tracking imperfections
- No augmentation changes the underlying class
"""

from .advanced_augmentation import AdvancedAugmentation, ComposeAugmentations
from .temporal_augmentation import TemporalScaling, TemporalReverse, TemporalJitter
from .pose_augmentation import PoseNoise, PoseScaling, JointMasking, SelectiveMasking

__all__ = [
    "AdvancedAugmentation",
    "ComposeAugmentations",
    "TemporalScaling",
    "TemporalReverse",
    "TemporalJitter",
    "PoseNoise",
    "PoseScaling",
    "JointMasking",
    "SelectiveMasking",
]
