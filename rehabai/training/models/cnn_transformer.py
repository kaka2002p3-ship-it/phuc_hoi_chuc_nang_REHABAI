import torch
import torch.nn as nn
import math

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, 1, d_model)
        pe[:, 0, 0::2] = torch.sin(position * div_term)
        pe[:, 0, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Arguments:
            x: Tensor, shape ``[seq_len, batch_size, embedding_dim]``
        """
        x = x + self.pe[:x.size(0)]
        return self.dropout(x)

class RehabModel(nn.Module):
    def __init__(self, num_classes: int, input_dim: int = 237, 
                 hidden_dim: int = 128, nhead: int = 4, 
                 num_layers: int = 3, dropout: float = 0.2):
        super(RehabModel, self).__init__()
        
        # 1D-CNN for local temporal feature extraction
        # Input shape: (Batch, Channels, Length) -> (B, input_dim, T)
        self.cnn = nn.Sequential(
            nn.Conv1d(in_channels=input_dim, out_channels=hidden_dim, kernel_size=3, padding=1),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Conv1d(in_channels=hidden_dim, out_channels=hidden_dim, kernel_size=3, padding=1),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        # Positional Encoding
        self.pos_encoder = PositionalEncoding(d_model=hidden_dim, dropout=dropout)
        
        # Transformer Encoder
        encoder_layers = nn.TransformerEncoderLayer(d_model=hidden_dim, nhead=nhead, 
                                                    dim_feedforward=hidden_dim*4, 
                                                    dropout=dropout, batch_first=False)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers=num_layers)
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, T, InputDim)
        
        # CNN expects (B, Channels, Length)
        x = x.permute(0, 2, 1) # (B, InputDim, T)
        x = self.cnn(x) # (B, HiddenDim, T)
        
        # Transformer expects (T, B, HiddenDim) if batch_first=False
        x = x.permute(2, 0, 1) # (T, B, HiddenDim)
        
        x = self.pos_encoder(x)
        x = self.transformer_encoder(x) # (T, B, HiddenDim)
        
        # Global Average Pooling over time
        x = x.mean(dim=0) # (B, HiddenDim)
        
        out = self.classifier(x) # (B, NumClasses)
        return out
