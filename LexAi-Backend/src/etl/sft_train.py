# sft_train.py
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_int8_training

# ---------------- CONFIG ----------------
BASE_MODEL = "meta-llama/Llama-2-7b-hf"  # LLaMA-2 HF
SFT_DATA = "sft_data.jsonl"              # Senin soru-cevap JSONL dosyan
OUTPUT_DIR = "./llama2-tr-sft"
MAX_LENGTH = 512
BATCH_SIZE = 2
GRAD_ACCUM = 4
NUM_EPOCHS = 3
LEARNING_RATE = 3e-4
# ----------------------------------------

print("Tokenizer ve model yükleniyor...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, device_map="auto")
model = prepare_model_for_int8_training(model)

print("⚡ LoRA SFT ayarlanıyor...")
peft_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,
    lora_alpha=32,
    target_modules=["q_proj","v_proj"],
    lora_dropout=0.05,
    bias="none"
)
model = get_peft_model(model, peft_config)

print("📚 Dataset yükleniyor...")
dataset = load_dataset("json", data_files=SFT_DATA)["train"]

def tokenize_fn(batch):
    texts = [p + " " + c for p, c in zip(batch["prompt"], batch["completion"])]
    return tokenizer(texts, truncation=True, padding="max_length", max_length=MAX_LENGTH)

tokenized_dataset = dataset.map(tokenize_fn, batched=True)
tokenized_dataset.set_format(type="torch", columns=["input_ids", "attention_mask"])

print("TrainingArguments ayarlanıyor...")
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRAD_ACCUM,
    num_train_epochs=NUM_EPOCHS,
    learning_rate=LEARNING_RATE,
    fp16=True,
    logging_steps=10,
    save_strategy="epoch",
    save_total_limit=2,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset
)

print("Eğitim başlıyor...")
trainer.train()

print("💾 Model kaydediliyor...")
trainer.save_model(OUTPUT_DIR)
print("Eğitim tamamlandı, model kaydedildi:", OUTPUT_DIR)
