# Sentinel Forge - Custom LLM Fine-Tuning & Deployment Playbook

This guide details the step-by-step process of preparing a task-specific cybersecurity dataset, fine-tuning a lightweight instruction-following model on your local **RTX 4050 6GB VRAM** GPU, converting the weights to **GGUF format**, and hosting it on a **Vultr CPU/GPU VPS** using Ollama.

---

## Part 1: Local Environment Setup (Windows)

We will use **BitsAndBytes (4-bit QLoRA)** and **TRL (SFTTrainer)** to fit model training within the **6GB VRAM** limitation.

### 1. Prerequisites
- Install [Git for Windows](https://git-scm.com/download/win).
- Install [Python 3.10, 3.11, or 3.12](https://www.python.org/downloads/) (HuggingFace library utilities perform best on these versions).
- Install the **CUDA Toolkit 11.8 or 12.1** (matching your PyTorch version) from [NVIDIA Developer](https://developer.nvidia.com/cuda-downloads).

### 2. Setup Virtual Environment
Run the following in PowerShell/Command Prompt inside the workspace:
```bash
# Create virtual environment (specify Python 3.12 executable if python defaults to 3.14 on path)
C:\Users\Pratham\AppData\Local\Programs\Python\Python312\python.exe -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows Command Prompt:
.\venv\Scripts\activate.bat
```

### 3. Install PyTorch with CUDA support
Install PyTorch compiled for CUDA:
```bash
# For CUDA 12.1:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 4. Install Training Libraries
Install the Hugging Face libraries and bitsandbytes (standard PyPI bitsandbytes now natively includes pre-compiled Windows wheels):
```bash
pip install transformers peft trl datasets accelerate bitsandbytes
```

---

## Part 2: Training Pipeline

All the scripts necessary for this pipeline are located in the `finetuning_a_model/` folder:
1. [prepare_dataset.py](file:///c:/Users/Pratham/Downloads/Final%20Year%20Project/finetuning_a_model/prepare_dataset.py)
2. [train.py](file:///c:/Users/Pratham/Downloads/Final%20Year%20Project/finetuning_a_model/train.py)
3. [export_and_merge.py](file:///c:/Users/Pratham/Downloads/Final%20Year%20Project/finetuning_a_model/export_and_merge.py)

### Step 1: Synthesize the Multi-Task Dataset
Run the preparation script to generate `train_data.jsonl`, compiling 4,700+ rows covering Intent, Analysis, Report, and Response schema prompts:
```bash
python finetuning_a_model/prepare_dataset.py
```

### Step 2: Run the Fine-Tuning Loop
Run the SFTTrainer loop to load `Qwen2.5-Coder-1.5B-Instruct` in 4-bit, train adapters, and export them:
```bash
python finetuning_a_model/train.py
```
*Note: SFTTrainer uses gradient checkpointing and a batch size of 1 with gradient accumulation of 8 to prevent CUDA OOM on your 6GB card.*

### Step 3: Merge Adapters
Merge the trained LoRA adapters back into a complete consolidated FP16 base model weights:
```bash
python finetuning_a_model/export_and_merge.py
```

---

## Part 3: Quantization to GGUF (via llama.cpp)

To run the model efficiently on a cheap CPU-only Vultr VPS (or locally with minimum memory overhead), we must quantize the merged model to 4-bit GGUF.

### 1. Clone llama.cpp
Clone the repository and set up its requirements:
```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# Create a clean venv for llama.cpp tools
python -m venv llama_venv
.\llama_venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Convert PyTorch model to GGUF
Since native 4-bit quantizations (like `q4_k_m`) require a compiled C++ environment (`llama-quantize`), we use python-based native 8-bit quantization (`q8_0`), which converts directly on Windows without requiring extra compiler tooling, producing a high-performance 1.6GB GGUF model:
```bash
python convert_hf_to_gguf.py ../merged_model --outfile ../sentinel-forge-qwen.gguf --outtype q8_0
```
This generates `sentinel-forge-qwen.gguf` under the `finetuning_a_model/` folder.

---

## Part 4: Ollama Deployment (Vultr VPS / Local)

Once you have your `sentinel-forge-qwen.gguf` model file:

### 1. Create a Modelfile
Under the `finetuning_a_model/` folder, create a file named `Modelfile` with the following contents:
```dockerfile
FROM ./sentinel-forge-qwen.gguf

# Set ChatML template structure mapping system prompts correctly
TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ .Response }}<|im_end|>"""

SYSTEM """You are Sentinel Forge AI, a custom cybersecurity log intelligence assistant. You help categorize intent classes, analyze server metrics, write executive threat reports, and suggest mitigation commands. Always format your outputs in strict JSON if requested."""

PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
PARAMETER num_ctx 4096
PARAMETER temperature 0.2
```

### 2. Register the Model locally in Ollama
Run the creation command matching your current terminal directory (passing the wrong path causes Ollama to fall back to pulling from registry and crash with a GGUF format error):

* **If your terminal is in the project root folder (`Final Year Project/`):**
  ```bash
  ollama create sentinel-forge-qwen -f finetuning_a_model/Modelfile
  ```

* **If your terminal is inside the `finetuning_a_model/` folder:**
  ```bash
  ollama create sentinel-forge-qwen -f Modelfile
  ```

* **Verify it works locally:**
  ```bash
  ollama run sentinel-forge-qwen "Detect brute force login attacks and isolate the offender IP."
  ```

---

## Part 5: Uploading Model to Ollama Registry

Rather than manually copying the large 1.6GB GGUF file to your remote VPS, you can push the model directly to the Ollama library. This allows you to pull the model on any machine using `ollama pull`.

### Step 1: Set Up your Ollama Account
1. Go to [ollama.com/signup](https://ollama.com/signup) and create an account. Choose a unique username (referred to as your `<namespace>`).
2. Once signed in, go to your profile settings and add your public SSH key:
   - On **Windows**, open your public key file at `C:\Users\<Your-Username>\.ollama\id_ed25519.pub` and copy its contents.
   - On **Linux/macOS**, open `~/.ollama/id_ed25519.pub`.
   *(If the key does not exist, run `ssh-keygen -t ed25519` or launch the Ollama app to auto-generate it).*
3. Paste the public key into the Ollama dashboard under **Keys**.

### Step 2: Tag (Copy) and Push the Model
In your local command line, duplicate the model using your namespace and push it:
```bash
# Copy the model to apply your registry namespace (this acts as tagging)
ollama cp sentinel-forge-qwen <your-namespace>/sentinel-forge-qwen

# Push the model to the Ollama registry
ollama push <your-namespace>/sentinel-forge-qwen
```
*This uploads the weights to Ollama's servers. Once completed, your model will be publicly pullable at `ollama.com/<your-namespace>/sentinel-forge-qwen`.*

---

## Part 6: Remote VPS Setup (Ubuntu)

Follow these steps to spin up a Vultr VPS, install Ollama, configure it for remote access, and pull your custom model.

### Step 1: Install Ollama on the VPS
SSH into your remote Vultr VPS instance (e.g. running Ubuntu 22.04 / 24.04 LTS):
```bash
# Connect to your VPS
ssh root@<your-vps-ip>

# Download and run the official Ollama installer script
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2: Configure Ollama for Remote Access
By default, Ollama only listens on `127.0.0.1:11434`. To allow your React frontend or Python orchestrator to connect to the VPS, we must bind it to `0.0.0.0`:

1. Open the systemd override editor for the Ollama service:
   ```bash
   sudo systemctl edit ollama.service
   ```
2. This opens a text editor. Insert the following lines at the top of the file (between the comments or at the very top):
   ```ini
   [Service]
   Environment="OLLAMA_HOST=0.0.0.0"
   ```
3. Save and close the editor (for `nano`, press `Ctrl+O`, `Enter`, then `Ctrl+X`).
4. Reload the systemd daemon and restart the Ollama service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart ollama
   ```
5. Verify Ollama is listening on all interfaces:
   ```bash
   ss -tlnp | grep 11434
   # You should see: LISTEN 0 512 0.0.0.0:11434
   ```

### Step 3: Open Firewall Port
If your VPS has `ufw` enabled, make sure port `11434` is open:
```bash
sudo ufw allow 11434/tcp
sudo ufw reload
```

### Step 4: Pull Your Custom Model on the VPS
Since the model is registered on the Ollama servers, you do not need to copy the GGUF. Simply pull it directly on the VPS:
```bash
ollama pull <your-namespace>/sentinel-forge-qwen
```

---

## Part 7: Connect Model to Sentinel Forge App

Now, route your log intelligence pipeline to your VPS instance:

1. Launch your **Sentinel Forge** React dashboard (web interface or Electron client).
2. Open the **Settings** drawer (toggle settings icon in the top header).
3. Configure the provider variables:
   - **LLM Provider**: Select `Ollama` from the dropdown.
   - **Custom Endpoint (API Base)**: Enter your remote VPS URL: `http://<your-vps-ip>:11434` (or `http://<your-vps-ip>:11434/v1` for OpenAI endpoint routing).
4. Click **Load Models from Endpoint**:
   - The application will communicate with your VPS's Ollama instance and automatically pull the active model list.
   - Select your custom model `<your-namespace>/sentinel-forge-qwen` from the dropdown.
5. Close the drawer and run the log analysis pipeline. Your custom agent model will process all inputs with zero rate limits!
