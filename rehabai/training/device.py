import os
import torch

def select_training_device():
    if not torch.cuda.is_available():
        raise RuntimeError(
            "RehabAI training requires a discrete NVIDIA CUDA GPU. "
            "CPU/iGPU fallback is disabled."
        )

    count = torch.cuda.device_count()
    override = os.getenv("REHABAI_CUDA_DEVICE")

    if override is not None:
        idx = int(override)
        if idx < 0 or idx >= count:
            raise RuntimeError(f"Invalid REHABAI_CUDA_DEVICE={idx}")
    else:
        idx = max(
            range(count),
            key=lambda i: torch.cuda.get_device_properties(i).total_memory
        )

    torch.cuda.set_device(idx)
    prop = torch.cuda.get_device_properties(idx)

    allow_other = os.getenv("REHABAI_ALLOW_OTHER_NVIDIA_GPU", "0")
    if allow_other != "1" and "RTX 4060 Laptop GPU" not in prop.name:
        raise RuntimeError(
            f"Expected NVIDIA GeForce RTX 4060 Laptop GPU, got: {prop.name}"
        )

    print(f"[GPU] cuda:{idx}")
    print(f"[GPU] {prop.name}")
    print(f"[GPU] VRAM={prop.total_memory / 1024**3:.2f} GB")
    print(f"[CUDA] torch={torch.__version__}")
    print(f"[CUDA] runtime={torch.version.cuda}")
    print(f"[cuDNN] {torch.backends.cudnn.version()}")

    test = torch.randn(1024, 1024, device=f"cuda:{idx}")
    _ = test @ test.T
    torch.cuda.synchronize(idx)

    return torch.device(f"cuda:{idx}")

if __name__ == "__main__":
    select_training_device()
