import torch
import torch.nn as nn
import torch.nn.functional as F

class SimCLR(nn.Module):
    """
    SimCLR framework for Self-Supervised Learning.
    Attaches a projection head to the base encoder.
    """
    def __init__(self, encoder, hidden_dim=128, projection_dim=128):
        super().__init__()
        self.encoder = encoder
        
        # Projection head (MLP with 1 hidden layer)
        self.projector = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, projection_dim)
        )

    def forward(self, x_i, x_j):
        """
        x_i: augmented view 1
        x_j: augmented view 2
        """
        h_i = self.encoder(x_i)
        h_j = self.encoder(x_j)
        
        z_i = self.projector(h_i)
        z_j = self.projector(h_j)
        
        return z_i, z_j

class NTXentLoss(nn.Module):
    """
    Normalized Temperature-scaled Cross Entropy Loss.
    """
    def __init__(self, temperature=0.1):
        super().__init__()
        self.temperature = temperature
        self.criterion = nn.CrossEntropyLoss()

    def forward(self, z_i, z_j):
        """
        z_i: (B, D)
        z_j: (B, D)
        """
        batch_size = z_i.shape[0]
        
        # Normalize representations
        z_i = F.normalize(z_i, dim=1)
        z_j = F.normalize(z_j, dim=1)
        
        # Concatenate all representations: (2B, D)
        z = torch.cat([z_i, z_j], dim=0)
        
        # Compute similarity matrix: (2B, 2B)
        sim_matrix = torch.matmul(z, z.T) / self.temperature
        
        # Mask out self-similarity on the diagonal
        mask = torch.eye(2 * batch_size, dtype=torch.bool).to(z.device)
        sim_matrix.masked_fill_(mask, -9e15)
        
        # Ground truth labels for contrastive learning
        # For z_i[k], the positive is z_j[k] (which is at index k + batch_size)
        # For z_j[k], the positive is z_i[k] (which is at index k)
        labels = torch.cat([torch.arange(batch_size, 2 * batch_size),
                            torch.arange(batch_size)], dim=0).to(z.device)
                            
        loss = self.criterion(sim_matrix, labels)
        return loss
