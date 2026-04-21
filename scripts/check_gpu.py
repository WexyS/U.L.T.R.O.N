import torch

def check_gpu():
    print("--- Ultron Factory GPU Check ---")
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")
    
    if cuda_available:
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"Memory Usage: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")
    else:
        print("WARNING: CUDA not found. Training will be extremely slow on CPU.")
        print("Ensure you have installed torch with CUDA support.")

if __name__ == "__main__":
    check_gpu()
