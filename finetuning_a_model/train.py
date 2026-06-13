import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

# ----------------- CONFIGURATIONS -----------------
MODEL_NAME = "Qwen/Qwen2.5-Coder-1.5B-Instruct"  # Lightweight and highly proficient in JSON
DATASET_PATH = "train_data.jsonl"
OUTPUT_DIR = "results"
LORA_OUTPUT_DIR = "lora_adapters"

print(f"Loading tokenizer and model: {MODEL_NAME}...")

# Tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

# 4-bit Quantization Config (BNB)
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

# Load Model
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
)

# Prepare model for PEFT training (e.g. gradient checkpointing, layer freezing)
model = prepare_model_for_kbit_training(model)

# LoRA Config
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj"
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

# ----------------- LOAD & FORMAT DATASET -----------------
print(f"Loading training dataset: {DATASET_PATH}...")

# Load custom JSONL dataset
dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

def format_prompts(batch):
    """
    Format chat messages into standard Qwen chat template.
    Expects batch['messages'] containing:
    [{'role': 'system', 'content': ...}, {'role': 'user', 'content': ...}, {'role': 'assistant', 'content': ...}]
    """
    texts = []
    for messages in batch["messages"]:
        # Apply the model's standard chat template tokenizer
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        texts.append(text)
    return {"text": texts}

formatted_dataset = dataset.map(format_prompts, batched=True)

# ----------------- TRAINING ARGUMENTS -----------------
print("Configuring SFTConfig arguments...")

sft_config = SFTConfig(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=1,            # 1 to avoid local CUDA OOM on 6GB VRAM
    gradient_accumulation_steps=8,            # Effective batch size = 8
    learning_rate=2e-4,                       # Standard LoRA learning rate
    logging_steps=10,
    save_strategy="steps",
    save_steps=100,
    max_steps=300,                            # Fine-tune steps (adjust as needed)
    optim="paged_adamw_32bit",                # Essential VRAM optimization for 6GB VRAM
    bf16=True,                                # Use bfloat16 precision (Ada GPU native)
    gradient_checkpointing=True,              # Drastically reduces VRAM footprint
    report_to="none",                         # Disable wandb/tensorboard logging
    warmup_ratio=0.03,
    dataset_text_field="text",                # Moved to SFTConfig for TRL >= 0.12/1.0
    max_length=1024,                          # Moved to SFTConfig for TRL >= 0.12/1.0
)

# ----------------- INITIALIZE SFTTRAINER -----------------
trainer = SFTTrainer(
    model=model,
    train_dataset=formatted_dataset,
    processing_class=tokenizer,               # Renamed from tokenizer in newer TRL
    args=sft_config,
)

print("Starting training loop...")
trainer.train()

print(f"Saving fine-tuned LoRA adapters to: {LORA_OUTPUT_DIR}...")
trainer.model.save_pretrained(LORA_OUTPUT_DIR)
tokenizer.save_pretrained(LORA_OUTPUT_DIR)

print("Training completed successfully!")
