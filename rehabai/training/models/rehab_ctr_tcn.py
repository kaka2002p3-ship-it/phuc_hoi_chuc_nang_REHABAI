"""Exercise-specific 3-stream CTR-GCN + MS-TCN correctness model.

The model deliberately has no exercise-classification or phase head. Phase and
rep-boundary supervision is not present in the current verified dataset.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


HAND_EDGES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
              (0, 9), (9, 10), (10, 11), (11, 12), (0, 13), (13, 14), (14, 15),
              (15, 16), (0, 17), (17, 18), (18, 19), (19, 20)]
ELBOW_EDGES = [(0, 1), (1, 2), (2, 3)]


def adjacency(nodes: int, edges: list[tuple[int, int]]) -> torch.Tensor:
    matrix = torch.eye(nodes, dtype=torch.float32)
    for source, target in edges:
        matrix[source, target] = matrix[target, source] = 1.0
    degree = matrix.sum(1).clamp_min(1).pow(-0.5)
    return degree[:, None] * matrix * degree[None, :]


def bone_features(joints: torch.Tensor, parents: list[int]) -> torch.Tensor:
    parent_index = torch.as_tensor(parents, device=joints.device)
    return joints - joints.index_select(2, parent_index)


def motion_features(joints: torch.Tensor) -> torch.Tensor:
    return torch.cat((torch.zeros_like(joints[:, :1]), joints[:, 1:] - joints[:, :-1]), dim=1)


class CTRBlock(nn.Module):
    def __init__(self, nodes: int, in_channels: int, out_channels: int, base_adj: torch.Tensor, dropout: float):
        super().__init__()
        self.register_buffer("base_adj", base_adj.clone())
        self.channel_relation = nn.Parameter(torch.zeros(out_channels, nodes, nodes))
        self.input_projection = nn.Conv2d(in_channels, out_channels, 1)
        self.temporal = nn.Conv2d(out_channels, out_channels, (3, 1), padding=(1, 0))
        self.norm = nn.BatchNorm2d(out_channels)
        self.dropout = nn.Dropout(dropout)
        self.residual = nn.Conv2d(in_channels, out_channels, 1) if in_channels != out_channels else nn.Identity()

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        residual = self.residual(value)
        projected = self.input_projection(value)
        relation = torch.softmax(self.channel_relation + self.base_adj.unsqueeze(0), dim=-1)
        projected = torch.einsum("bctv,cvw->bctw", projected, relation)
        return F.relu(self.norm(self.temporal(projected)) + residual).pipe(self.dropout) if hasattr(torch.Tensor, "pipe") else self.dropout(F.relu(self.norm(self.temporal(projected)) + residual))


class StreamEncoder(nn.Module):
    def __init__(self, nodes: int, graph: torch.Tensor, channels=(32, 32, 64, 64), dropout=.3):
        super().__init__()
        blocks, current = [], 3
        for width in channels:
            blocks.append(CTRBlock(nodes, current, width, graph, dropout))
            current = width
        self.blocks = nn.ModuleList(blocks)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        value = value.permute(0, 3, 1, 2)  # B,C,T,V
        for block in self.blocks:
            value = block(value)
        return value.mean(-1)  # B,C,T


class TemporalStage(nn.Module):
    def __init__(self, channels: int, layers: int, dropout: float):
        super().__init__()
        self.layers = nn.ModuleList([
            nn.Sequential(nn.Conv1d(channels, channels, 3, padding=2 ** index, dilation=2 ** index),
                          nn.BatchNorm1d(channels), nn.ReLU(), nn.Dropout(dropout))
            for index in range(layers)
        ])

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        for layer in self.layers:
            value = value + layer(value)
        return value


class RehabCTRTCN(nn.Module):
    def __init__(self, exercise: str, channels=(32, 32, 64, 64), fusion_dim=96,
                 mstcn_stages=2, mstcn_layers=3, attention_dim=48, dropout=.3):
        super().__init__()
        if exercise not in {"HAND_OPENING", "ELBOW_EXTENSION", "ELBOW_FLEXION"}:
            raise ValueError(f"Unsupported exercise: {exercise}")
        self.exercise = exercise
        nodes, edges = (21, HAND_EDGES) if exercise == "HAND_OPENING" else (4, ELBOW_EDGES)
        graph = adjacency(nodes, edges)
        self.parents = ([0, 0, 1, 2, 3, 0, 5, 6, 7, 0, 9, 10, 11, 0, 13, 14, 15, 0, 17, 18, 19]
                        if exercise == "HAND_OPENING" else [0, 0, 1, 2])
        self.joint_stream = StreamEncoder(nodes, graph, channels, dropout)
        self.bone_stream = StreamEncoder(nodes, graph, channels, dropout)
        self.motion_stream = StreamEncoder(nodes, graph, channels, dropout)
        self.fusion = nn.Sequential(nn.Conv1d(channels[-1] * 3, fusion_dim, 1),
                                    nn.BatchNorm1d(fusion_dim), nn.GELU(), nn.Dropout(dropout))
        self.stages = nn.ModuleList([TemporalStage(fusion_dim, mstcn_layers, dropout) for _ in range(mstcn_stages)])
        self.attention = nn.Sequential(nn.Conv1d(fusion_dim, attention_dim, 1), nn.Tanh(),
                                       nn.Conv1d(attention_dim, 1, 1))
        self.classifier = nn.Sequential(nn.Linear(fusion_dim, 64), nn.ReLU(), nn.Dropout(dropout), nn.Linear(64, 1))

    def forward(self, joints: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if joints.ndim != 4 or joints.shape[-1] != 3:
            raise ValueError(f"Expected (B,T,V,3), got {tuple(joints.shape)}")
        streams = (self.joint_stream(joints), self.bone_stream(bone_features(joints, self.parents)),
                   self.motion_stream(motion_features(joints)))
        temporal = self.fusion(torch.cat(streams, dim=1))
        for stage in self.stages:
            temporal = stage(temporal)
        weights = torch.softmax(self.attention(temporal), dim=-1)
        pooled = (temporal * weights).sum(-1)
        return self.classifier(pooled).squeeze(-1), temporal, weights.squeeze(1)
