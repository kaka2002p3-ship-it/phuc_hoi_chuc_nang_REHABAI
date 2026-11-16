import torch
import torch.nn as nn
import torch.nn.functional as F

class MultiScaleTCNBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        # 3 parallel branches with different dilations
        self.conv1 = nn.Conv1d(in_channels, out_channels // 3, kernel_size=3, padding=1, dilation=1)
        self.conv2 = nn.Conv1d(in_channels, out_channels // 3, kernel_size=3, padding=2, dilation=2)
        self.conv3 = nn.Conv1d(in_channels, out_channels - 2*(out_channels//3), kernel_size=3, padding=4, dilation=4)
        self.bn = nn.BatchNorm1d(out_channels)
        self.relu = nn.ReLU()
        
        # Residual connection if channels differ
        self.residual = nn.Conv1d(in_channels, out_channels, kernel_size=1) if in_channels != out_channels else nn.Identity()

    def forward(self, x):
        res = self.residual(x)
        c1 = self.conv1(x)
        c2 = self.conv2(x)
        c3 = self.conv3(x)
        out = torch.cat([c1, c2, c3], dim=1)
        out = self.bn(out)
        out = self.relu(out + res)
        return out

class SharedMotionEncoder(nn.Module):
    """
    Lightweight MS-TCN for Representation Learning.
    Input: (B, T, 237)
    Output: (B, hidden_dim)
    """
    def __init__(self, input_dim=237, hidden_dim=128, channels=[64, 128, 256]):
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        layers = []
        in_c = input_dim
        for out_c in channels:
            layers.append(MultiScaleTCNBlock(in_c, out_c))
            in_c = out_c
            
        self.encoder = nn.Sequential(*layers)
        self.pool = nn.AdaptiveAvgPool1d(1)
        
        # Output projection to final hidden_dim
        self.proj = nn.Linear(channels[-1], hidden_dim)

    def forward(self, x):
        # x: (B, T, C) -> (B, C, T) for Conv1d
        x = x.permute(0, 2, 1)
        
        x = self.encoder(x) # (B, C_out, T)
        
        # Global pooling
        x = self.pool(x).squeeze(-1) # (B, C_out)
        
        out = self.proj(x) # (B, hidden_dim)
        return out
