import torch
import subprocess
import os

# Force CUDA detection
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
if torch.cuda.is_available():
    print("CUDA is available")
else:
    print("CUDA not available, using CPU")

def check_nvidia_smi():
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        print("NVIDIA-SMI Output:")
        print(result.stdout)
        return True
    except Exception as e:
        print(f"Error running nvidia-smi: {e}")
        return False

print("Checking GPU information...")
check_nvidia_smi()
print(f"\ncuda available: {torch.cuda.is_available()}")
print("\nCUDA_HOME:", os.environ.get('CUDA_HOME'))
print("CUDA_PATH:", os.environ.get('CUDA_PATH'))