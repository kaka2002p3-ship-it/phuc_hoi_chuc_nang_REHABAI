import torch
import torch.nn as nn
from training.models.shared_encoder import SharedMotionEncoder, MultiScaleTCNBlock

class PoseGraphBranch(nn.Module):
    def __init__(self, in_channels=3, out_channels=64, num_nodes=33, node_indices=None):
        super().__init__()
        self.num_nodes = num_nodes
        self.node_indices = node_indices
        self.A = nn.Parameter(torch.rand(num_nodes, num_nodes))
        self.spatial_conv = nn.Conv2d(in_channels, out_channels, kernel_size=1)
        self.temporal_conv = nn.Conv2d(out_channels, out_channels, kernel_size=(3, 1), padding=(1, 0))
        self.relu = nn.ReLU()

    def forward(self, x):
        # x: (B, T, V*C) -> (B, C, T, V)
        B, T, _ = x.shape
        x = x.view(B, T, 33, 3)
        if self.node_indices is not None:
            x = x[:, :, self.node_indices, :]
        x = x.permute(0, 3, 1, 2)
        ax = torch.einsum('bctv,vw->bctw', x, self.A)
        out = self.relu(self.spatial_conv(ax))
        out = self.relu(self.temporal_conv(out))
        # Pool over nodes -> (B, C, T)
        return out.mean(dim=-1)

class HandBranch(nn.Module):
    def __init__(self, in_channels=126, out_channels=32):
        super().__init__()
        self.conv = nn.Conv1d(in_channels, out_channels, kernel_size=3, padding=1)
        self.relu = nn.ReLU()

    def forward(self, x):
        # x: (B, T, C) -> (B, C, T)
        x = x.permute(0, 2, 1)
        return self.relu(self.conv(x))

class KinematicBranch(nn.Module):
    def __init__(self, in_channels=12, out_channels=32):
        super().__init__()
        self.conv = nn.Conv1d(in_channels, out_channels, kernel_size=3, padding=1)
        self.relu = nn.ReLU()

    def forward(self, x):
        # x: (B, T, C) -> (B, C, T)
        x = x.permute(0, 2, 1)
        return self.relu(self.conv(x))


class ExternalEncoderAdapter(nn.Module):
    """Frozen external motion encoder with a small target-domain adapter.

    The external encoder is intentionally evaluated without gradients.  This
    keeps the source representation fixed while the compact adapter and task
    heads learn only from the LOSO training subjects in data 01.
    """

    def __init__(self, num_exercises=4, adapter_dim=64, adapter_dropout=0.20):
        super().__init__()
        self.pretrained_encoder = SharedMotionEncoder()
        self.adapter = nn.Sequential(
            nn.LayerNorm(128),
            nn.Linear(128, adapter_dim),
            nn.GELU(),
            nn.Dropout(adapter_dropout),
        )
        self.ex_head = nn.Linear(adapter_dim, num_exercises)
        self.comp_head = nn.Linear(adapter_dim, 1)

    def freeze_encoder(self):
        self.pretrained_encoder.eval()
        for parameter in self.pretrained_encoder.parameters():
            parameter.requires_grad_(False)

    def train(self, mode=True):
        super().train(mode)
        # ``model.train()`` must not update BatchNorm running statistics in the
        # frozen source encoder, otherwise the representation is not frozen.
        self.pretrained_encoder.eval()
        return self

    def forward(self, x):
        with torch.no_grad():
            encoded = self.pretrained_encoder(x)
        adapted = self.adapter(encoded)
        return self.ex_head(adapted), self.comp_head(adapted)


class OptimizedSSLAdapter(nn.Module):
    """Optimized-v1 plus a frozen cross-domain IntelliRehab SSL feature.

    The supervised path is exactly the predeclared Optimized-v1 architecture:
    upper-limb pose, both hands, kinematics and MS-TCN, without attention or
    the legacy contrastive branch.  The source encoder sees only the common
    Kinect/MediaPipe view and therefore cannot rely on invented hand joints.
    """

    COMMON_POSE_JOINTS = (11, 12, 13, 14, 15, 16, 23, 24)

    def __init__(self, num_exercises=4, adapter_dim=64, adapter_dropout=0.20):
        super().__init__()
        self.pose_branch = PoseGraphBranch(
            in_channels=3,
            out_channels=64,
            num_nodes=6,
            node_indices=[11, 12, 13, 14, 15, 16],
        )
        self.hand_branch = HandBranch(in_channels=126, out_channels=32)
        self.kinematic_branch = KinematicBranch(in_channels=12, out_channels=32)
        self.mstcn = nn.Sequential(
            MultiScaleTCNBlock(128, 128),
            MultiScaleTCNBlock(128, 128),
        )
        self.ssl_encoder = SharedMotionEncoder()
        self.ssl_adapter = nn.Sequential(
            nn.LayerNorm(128),
            nn.Linear(128, adapter_dim),
            nn.GELU(),
            nn.Dropout(adapter_dropout),
        )
        self.ex_head = nn.Linear(128 + adapter_dim, num_exercises)
        self.comp_head = nn.Linear(128 + adapter_dim, 1)
        self.freeze_encoder()

    def freeze_encoder(self):
        self.ssl_encoder.eval()
        for parameter in self.ssl_encoder.parameters():
            parameter.requires_grad_(False)

    def train(self, mode=True):
        super().train(mode)
        self.ssl_encoder.eval()
        return self

    @classmethod
    def common_view(cls, x):
        if x.ndim != 3 or x.shape[-1] != 237:
            raise ValueError(f"Expected input (B,T,237), got {tuple(x.shape)}")
        common = torch.zeros_like(x)
        for joint in cls.COMMON_POSE_JOINTS:
            start = joint * 3
            common[:, :, start:start + 3] = x[:, :, start:start + 3]
        # The product loader uses fold-level kinematic normalization, while
        # IntelliRehab SSL uses per-sequence normalization. Re-standardizing
        # here makes the source/target common-view contract identical.
        kin = x[:, :, 225:237]
        mean = kin.mean(dim=1, keepdim=True)
        std = kin.std(dim=1, keepdim=True, unbiased=False).clamp_min(1e-5)
        common[:, :, 225:237] = (kin - mean) / std
        return common

    def forward(self, x):
        pose = self.pose_branch(x[:, :, 0:99])
        hands = self.hand_branch(x[:, :, 99:225])
        kinematics = self.kinematic_branch(x[:, :, 225:237])
        optimized = self.mstcn(torch.cat([pose, hands, kinematics], dim=1)).mean(dim=2)
        with torch.no_grad():
            source_feature = self.ssl_encoder(self.common_view(x))
        fused = torch.cat([optimized, self.ssl_adapter(source_feature)], dim=1)
        return self.ex_head(fused), self.comp_head(fused)

class RehabMotionNet(nn.Module):
    def __init__(self, num_exercises=4, 
                 use_hand=True, use_kinematic=True, use_contrastive=True, 
                 use_mstcn=True, use_attention=True, upper_limb_only=False):
        super().__init__()
        
        self.use_hand = use_hand
        self.use_kinematic = use_kinematic
        self.use_contrastive = use_contrastive
        self.use_mstcn = use_mstcn
        self.use_attention = use_attention
        self.upper_limb_only = upper_limb_only
        
        # Branches
        arm_nodes = [11, 12, 13, 14, 15, 16] if upper_limb_only else None
        self.pose_branch = PoseGraphBranch(
            in_channels=3, out_channels=64,
            num_nodes=6 if upper_limb_only else 33,
            node_indices=arm_nodes,
        )
        
        fusion_dim = 64
        if self.use_hand:
            self.hand_branch = HandBranch(in_channels=126, out_channels=32)
            fusion_dim += 32
        if self.use_kinematic:
            self.kinematic_branch = KinematicBranch(in_channels=12, out_channels=32)
            fusion_dim += 32
            
        # Temporal Fusion (MS-TCN)
        if self.use_mstcn:
            self.mstcn = nn.Sequential(
                MultiScaleTCNBlock(fusion_dim, 128),
                MultiScaleTCNBlock(128, 128)
            )
            fusion_dim = 128
            
        # Attention
        if self.use_attention:
            self.attn = nn.MultiheadAttention(embed_dim=fusion_dim, num_heads=4, batch_first=True)
            
        final_dim = fusion_dim
        
        # Contrastive Pretrained Encoder
        if self.use_contrastive:
            self.pretrained_encoder = SharedMotionEncoder()
            # In training script, we will load weights and freeze it
            final_dim += 128
            
        # Multi-task Heads
        self.ex_head = nn.Linear(final_dim, num_exercises)
        self.comp_head = nn.Linear(final_dim, 1)

    def forward(self, x):
        B, T, _ = x.shape
        
        # Slicing inputs
        pose = x[:, :, 0:99]
        lh = x[:, :, 99:162]
        rh = x[:, :, 162:225]
        kin = x[:, :, 225:237]
        
        # Branch forward
        p_feat = self.pose_branch(pose) # (B, 64, T)
        feats = [p_feat]
        
        if self.use_hand:
            h_feat = self.hand_branch(torch.cat([lh, rh], dim=-1))
            feats.append(h_feat)
        if self.use_kinematic:
            k_feat = self.kinematic_branch(kin)
            feats.append(k_feat)
            
        # Concatenate features
        fused = torch.cat(feats, dim=1) # (B, fusion_dim, T)
        
        # Temporal Fusion
        if self.use_mstcn:
            fused = self.mstcn(fused)
            
        # Attention requires (B, T, C)
        fused = fused.permute(0, 2, 1)
        if self.use_attention:
            attn_out, _ = self.attn(fused, fused, fused)
            fused = fused + attn_out # Residual connection
            
        # Global Temporal Pooling -> (B, fusion_dim)
        fused = fused.mean(dim=1)
        
        # Integrate Pretrained
        if self.use_contrastive:
            with torch.no_grad():
                pretrained_feat = self.pretrained_encoder(x) # (B, 128)
            fused = torch.cat([fused, pretrained_feat], dim=-1) # (B, final_dim)
            
        # Heads
        out_ex = self.ex_head(fused)
        out_comp = self.comp_head(fused)
        
        return out_ex, out_comp
