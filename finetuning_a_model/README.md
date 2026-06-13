# Custom LLM Fine-Tuning - Quickstart Guide

This directory contains the workspace and scripts to compile the cybersecurity training dataset, fine-tune Qwen/Llama models locally on your **RTX 4050 6GB VRAM** GPU, and export the weights.

---

## ⚡ Quickstart Steps

### Step 1: Initialize the Environment (Windows)
Open PowerShell in the project root and run:
```powershell
# Navigate to the workspace (if needed)
cd "c:\Users\Pratham\Downloads\Final Year Project"

# Create a virtual environment using Python 3.12 (ensures CUDA wheel support)
C:\Users\Pratham\AppData\Local\Programs\Python\Python312\python.exe -m venv venv

# Activate the environment
.\venv\Scripts\Activate.ps1

# Install PyTorch with CUDA 12.1 support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install dependencies (standard PyPI bitsandbytes supports Windows natively now)
pip install transformers peft trl datasets accelerate bitsandbytes
```

### Step 2: Generate the Dataset
Create the 4,700-row agent-specific training dataset:
```powershell
python finetuning_a_model/prepare_dataset.py
```
*This generates `finetuning_a_model/train_data.jsonl` containing structured training prompts.*

### Step 3: Run the Training Loop
Run the fine-tuning script to train LoRA adapters:
```powershell
python finetuning_a_model/train.py
```
*This script uses gradient checkpointing and memory-efficient optimizers to keep VRAM usage under 6GB.*

### Step 4: Merge Model Weights
Consolidate the trained LoRA adapters back into the float16 base model weights:
```powershell
python finetuning_a_model/export_and_merge.py
```
*This saves the final merged model in `finetuning_a_model/merged_model/`.*

---

## 🚀 Quantization and Deployment

Once training is complete, follow the step-by-step commands in the deployment guide to convert the merged weights to **GGUF format** and host them in Ollama:

👉 **[model_deployment.md](file:///c:/Users/Pratham/Downloads/Final%20Year%20Project/finetuning_a_model/model_deployment.md)**
