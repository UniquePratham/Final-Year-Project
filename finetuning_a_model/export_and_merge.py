import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# ----------------- CONFIGURATIONS -----------------
BASE_MODEL_NAME = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
LORA_ADAPTERS_PATH = "lora_adapters"
MERGED_OUTPUT_DIR = "merged_model"

print(f"Loading base model in float16: {BASE_MODEL_NAME}...")

# Load standard tokenizer
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME, trust_remote_code=True)

# Load base model in FP16 (Required for clean merging)
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL_NAME,
    torch_dtype=torch.float16,
    device_map="cpu",  # Run on CPU to avoid GPU VRAM limitations during merge
    trust_remote_code=True,
)

print(f"Loading LoRA adapters from: {LORA_ADAPTERS_PATH}...")

# Load PeftModel wrapper
model = PeftModel.from_pretrained(base_model, LORA_ADAPTERS_PATH)

print("Merging LoRA adapters into base model weights...")

# Merge adapters and unload PEFT hooks
merged_model = model.merge_and_unload()

print(f"Saving merged weights and tokenizer to: {MERGED_OUTPUT_DIR}...")

# Save merged model weights
merged_model.save_pretrained(MERGED_OUTPUT_DIR, safe_serialization=True)
# Save tokenizer configs
tokenizer.save_pretrained(MERGED_OUTPUT_DIR)

print("Merge completed successfully! The model is now ready for GGUF conversion.")
