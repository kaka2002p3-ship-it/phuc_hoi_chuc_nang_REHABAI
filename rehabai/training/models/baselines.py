import torch
import torch.nn as nn

class BaseModel(nn.Module):
    def __init__(self, input_dim=237, num_exercises=4):
        super().__init__()
        self.input_dim = input_dim
        self.num_exercises = num_exercises

    def forward(self, x):
        # x: (B, T, C)
        raise NotImplementedError

class MLPBaseline(BaseModel):
    def __init__(self, input_dim=237, num_exercises=4):
        super().__init__(input_dim, num_exercises)
        self.fc1 = nn.Linear(input_dim, 256)
        self.fc2 = nn.Linear(256, 128)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
        
        self.ex_head = nn.Linear(128, num_exercises)
        self.comp_head = nn.Linear(128, 1)

    def forward(self, x):
        # Global Average Pooling over time
        x = x.mean(dim=1) # (B, C)
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        
        out_ex = self.ex_head(x)
        out_comp = self.comp_head(x)
        return out_ex, out_comp

class LSTMBaseline(BaseModel):
    def __init__(self, input_dim=237, num_exercises=4, hidden_size=128, num_layers=2, bidirectional=False):
        super().__init__(input_dim, num_exercises)
        self.lstm = nn.LSTM(input_dim, hidden_size, num_layers, batch_first=True, bidirectional=bidirectional)
        
        fc_dim = hidden_size * 2 if bidirectional else hidden_size
        self.ex_head = nn.Linear(fc_dim, num_exercises)
        self.comp_head = nn.Linear(fc_dim, 1)

    def forward(self, x):
        out, _ = self.lstm(x) # out: (B, T, hidden_size)
        
        # Global Average Pooling over time
        x = out.mean(dim=1)
        
        out_ex = self.ex_head(x)
        out_comp = self.comp_head(x)
        return out_ex, out_comp

class BiLSTMBaseline(LSTMBaseline):
    def __init__(self, input_dim=237, num_exercises=4, hidden_size=128, num_layers=2):
        super().__init__(input_dim, num_exercises, hidden_size, num_layers, bidirectional=True)

class TCNBlock(nn.Module):
    def __init__(self, in_channels, out_channels, dilation):
        super().__init__()
        self.conv = nn.Conv1d(in_channels, out_channels, kernel_size=3, padding=dilation, dilation=dilation)
        self.relu = nn.ReLU()
    def forward(self, x):
        return self.relu(self.conv(x))

class TCNBaseline(BaseModel):
    def __init__(self, input_dim=237, num_exercises=4, channels=[64, 128, 128]):
        super().__init__(input_dim, num_exercises)
        layers = []
        in_c = input_dim
        for i, out_c in enumerate(channels):
            dilation = 2 ** i
            layers.append(TCNBlock(in_c, out_c, dilation))
            in_c = out_c
            
        self.tcn = nn.Sequential(*layers)
        self.ex_head = nn.Linear(channels[-1], num_exercises)
        self.comp_head = nn.Linear(channels[-1], 1)

    def forward(self, x):
        # x: (B, T, C) -> (B, C, T)
        x = x.permute(0, 2, 1)
        x = self.tcn(x)
        # GAP over time
        x = x.mean(dim=2)
        out_ex = self.ex_head(x)
        out_comp = self.comp_head(x)
        return out_ex, out_comp

class BasicSTGCN(BaseModel):
    def __init__(self, input_dim=237, num_exercises=4):
        super().__init__(input_dim, num_exercises)
        # Simplified ST-GCN block
        # Since skeletal graph is fixed, we use an learnable adjacency matrix
        # 33 pose + 21 LH + 21 RH = 75 nodes
        self.num_nodes = 75
        self.node_feat = 3
        
        # Learnable adjacency matrix
        self.A = nn.Parameter(torch.rand(self.num_nodes, self.num_nodes))
        
        self.spatial_conv = nn.Conv2d(self.node_feat, 64, kernel_size=1)
        self.temporal_conv = nn.Conv2d(64, 64, kernel_size=(3, 1), padding=(1, 0))
        
        self.relu = nn.ReLU()
        self.ex_head = nn.Linear(64, num_exercises)
        self.comp_head = nn.Linear(64, 1)

    def forward(self, x):
        B, T, C = x.shape
        # Extract spatial features only, ignore kinematics (last 12 features)
        spatial_x = x[:, :, :225].view(B, T, self.num_nodes, self.node_feat)
        
        # Reshape for conv2d: (B, C, T, V)
        spatial_x = spatial_x.permute(0, 3, 1, 2)
        
        # Spatial Conv (X * A * W)
        # spatial_x: (B, C, T, V), A: (V, V)
        # Using einsum for X * A
        ax = torch.einsum('bctv,vw->bctw', spatial_x, self.A)
        x_out = self.spatial_conv(ax)
        x_out = self.relu(x_out)
        
        # Temporal Conv
        x_out = self.temporal_conv(x_out)
        x_out = self.relu(x_out)
        
        # GAP over time and nodes
        x_out = x_out.mean(dim=(2, 3)) # (B, 64)
        
        out_ex = self.ex_head(x_out)
        out_comp = self.comp_head(x_out)
        return out_ex, out_comp
