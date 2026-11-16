"""Small confidence/mask-aware CTR-GCN-style model for upper-limb sequences.

This module provides the ChannelTopologyGCN and UpperLimbCTRGCN classes
for multi-branch pose/hand/kinematic classification on rehabilitation motion data.
"""
from __future__ import annotations

from typing import Tuple, List, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor


class ChannelTopologyGCN(nn.Module):
    """
    Graph Convolutional Network layer with learnable channel topology.

    Processes skeleton-based motion data by applying spatial graph operations
    followed by channel-wise mixing and temporal convolution.
    """

    def __init__(self, nodes: int, out_channels: int) -> None:
        """
        Args:
            nodes: Number of skeleton nodes
            out_channels: Output channel dimension
        """
        super().__init__()
        self.nodes = nodes
        self.out_channels = out_channels

        # Learnable adjacency matrices
        self.base_adj = nn.Parameter(torch.eye(nodes) + 0.05)
        self.channel_adj = nn.Parameter(torch.zeros(out_channels, nodes, nodes))

        # Feature projection
        self.proj = nn.Conv2d(3, out_channels, 1)

        # Temporal convolution
        self.temporal = nn.Conv2d(out_channels, out_channels, (3, 1), padding=(1, 0))

        # Normalization
        self.norm = nn.BatchNorm2d(out_channels)

    def forward(self, x: Tensor) -> Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor of shape (B, T, V, 3) where V is number of nodes

        Returns:
            Output tensor of shape (B, C_out, T, V)
        """
        # Mask invalid (all-zero) landmarks
        valid = (x.abs().sum(dim=-1, keepdim=True) > 1e-6).to(x.dtype)
        x = x * valid

        # (B, T, V, 3) -> (B, 3, T, V)
        x = x.permute(0, 3, 1, 2)

        # Spatial graph operation
        adj = torch.softmax(self.base_adj, dim=-1)
        mixed = torch.einsum("bctv,vw->bctw", x, adj)

        # Channel projection
        out = self.proj(mixed)

        # Channel-wise mixing
        channel_adj = torch.softmax(self.channel_adj, dim=-1)
        out = torch.einsum("bctv,cvw->bctw", out, channel_adj)

        # Temporal convolution
        out = self.temporal(out)

        return F.relu(self.norm(out))


class UpperLimbCTRGCN(nn.Module):
    """
    Multi-branch pose/hand/kinematic classifier for upper-limb rehabilitation.

    Architecture:
    - Pose branch: Graph CNN on upper-limb joints
    - Hand branches: Graph CNN on left/right hands
    - Kinematic branch: 1D CNN on joint angles/velocities
    - Fusion: Concat + gating mechanism
    - Heads: Exercise classification + completion scoring

    Input: (B, T, 237) where 237 = 99 pose + 63 left_hand + 63 right_hand + 12 kinematics
    Output: Tuple of (exercise_logits, completion_logits)
    """

    def __init__(
        self,
        num_exercises: int = 4,
        hidden: int = 64,
        use_hand: bool = True,
        use_kinematic: bool = True,
        upper_limb_only: bool = True,
        **kwargs
    ) -> None:
        """
        Args:
            num_exercises: Number of exercise classes
            hidden: Hidden dimension for branches
            use_hand: Whether to include hand branches
            use_kinematic: Whether to include kinematic branch
            upper_limb_only: Must be True (only upper-limb supported)
        """
        super().__init__()

        if not upper_limb_only:
            raise ValueError("UpperLimbCTRGCN is defined for upper_limb_only=True")

        self.num_exercises = num_exercises
        self.hidden = hidden
        self.use_hand = use_hand
        self.use_kinematic = use_kinematic

        # Upper limb joints: shoulders, elbows, wrists
        self.pose_nodes = [11, 12, 13, 14, 15, 16]

        # Pose branch (6 upper-limb nodes)
        self.pose = ChannelTopologyGCN(6, hidden)

        # Calculate fusion dimension
        fusion_dim = hidden

        # Hand branches (21 finger joints each)
        if use_hand:
            self.left_hand = ChannelTopologyGCN(21, hidden // 2)
            self.right_hand = ChannelTopologyGCN(21, hidden // 2)
            fusion_dim += hidden  # +hidden for both hands

        # Kinematic branch (angles + velocities)
        if use_kinematic:
            self.kin = nn.Sequential(
                nn.Conv1d(12, hidden // 2, 3, padding=1),
                nn.BatchNorm1d(hidden // 2),
                nn.ReLU(),
                nn.Conv1d(hidden // 2, hidden // 2, 3, padding=1),
                nn.ReLU(),
            )
            fusion_dim += hidden // 2

        # Fusion layers with gating
        self.fusion = nn.Sequential(
            nn.Conv1d(fusion_dim, 128, 3, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Conv1d(128, 128, 3, padding=2, dilation=2),
            nn.ReLU(),
        )

        # Gating mechanism
        self.gate = nn.Sequential(nn.Conv1d(128, 128, 1), nn.Sigmoid())

        # Output heads
        self.ex_head = nn.Linear(128, num_exercises)
        self.comp_head = nn.Linear(128, 1)

    def forward(self, x: Tensor) -> Tuple[Tensor, Tensor]:
        """
        Forward pass.

        Args:
            x: Input tensor of shape (B, T, 237)

        Returns:
            Tuple of:
            - exercise_logits: (B, num_exercises)
            - completion_logits: (B, 1)
        """
        if x.ndim != 3 or x.shape[-1] != 237:
            raise ValueError(f"Expected (B,T,237), got {tuple(x.shape)}")

        B, T, _ = x.shape

        # Extract pose landmarks and select upper-limb nodes
        pose = x[:, :, :99].reshape(B, T, 33, 3)[:, :, self.pose_nodes]

        # Extract hand landmarks
        lh = x[:, :, 99:162].reshape(B, T, 21, 3)
        rh = x[:, :, 162:225].reshape(B, T, 21, 3)

        # Branch forward passes
        features: List[Tensor] = [self.pose(pose).mean(-1)]

        if self.use_hand:
            features.extend([
                self.left_hand(lh).mean(-1),
                self.right_hand(rh).mean(-1)
            ])

        if self.use_kinematic:
            features.append(self.kin(x[:, :, 225:237].transpose(1, 2)))

        # Concatenate features
        fused = self.fusion(torch.cat(features, dim=1))

        # Apply gating
        fused = fused * self.gate(fused)

        # Global average pooling
        pooled = F.adaptive_avg_pool1d(fused, 1).squeeze(-1)

        # Output heads
        return self.ex_head(pooled), self.comp_head(pooled)
