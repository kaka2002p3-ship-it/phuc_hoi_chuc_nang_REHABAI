import torch; model = torch.jit.load("artifacts/model_v1/model.pt"); out = model(torch.randn(1, 96, 237)); print("Success!", out[0].shape)
