import torch

print("CUDA:", torch.cuda.is_available())
print("GPUs:", torch.cuda.device_count())
