# Fine-tune LoRA bằng Unsloth. Chạy trên Google Colab (GPU T4 miễn phí là đủ cho model 3B-8B 4-bit).
#
# Cách dùng trên Colab:
#   1. Runtime -> Change runtime type -> T4 GPU
#   2. Ô đầu tiên:  !pip install unsloth
#   3. Tải file datasets/sft.jsonl lên Colab (hoặc mount Google Drive)
#   4. Dán từng khối "# %%" dưới đây vào từng ô và chạy lần lượt
#
# Thư viện thay đổi nhanh: nếu một hàm báo lỗi, mở notebook mẫu mới nhất của Unsloth
# cho đúng dòng model đang dùng và đối chiếu tên tham số.

# %% 1. Cấu hình
BASE_MODEL = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"   # hoặc "unsloth/Llama-3.2-3B-Instruct-bnb-4bit"
DATA_FILE = "sft.jsonl"
MAX_SEQ_LEN = 4096        # ngữ cảnh RAG dài nên cần lớn
OUTPUT_NAME = "chatbot-hust-lora"

# %% 2. Tải model gốc ở dạng 4-bit (tiết kiệm VRAM)
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=BASE_MODEL,
    max_seq_length=MAX_SEQ_LEN,
    load_in_4bit=True,
)

# %% 3. Gắn LoRA: chỉ train thêm vài chục MB tham số, model gốc giữ nguyên
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=16,
    lora_dropout=0,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# %% 4. Dữ liệu: mỗi dòng {"messages": [...]}, chuyển thành văn bản theo chat template của model
from datasets import load_dataset

ds = load_dataset("json", data_files=DATA_FILE, split="train")
ds = ds.map(lambda ex: {"text": tokenizer.apply_chat_template(ex["messages"], tokenize=False)})
split = ds.train_test_split(test_size=0.05, seed=42)   # 5% để theo dõi overfit

# %% 5. Train
from trl import SFTConfig, SFTTrainer

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,             # bản TRL mới có thể đổi thành processing_class=tokenizer
    train_dataset=split["train"],
    eval_dataset=split["test"],
    args=SFTConfig(
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LEN,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=2,
        learning_rate=2e-4,
        warmup_steps=10,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        output_dir="outputs",
        report_to="none",
    ),
)
trainer.train()
# Theo dõi: train loss giảm đều; eval loss tăng trở lại => đang overfit, giảm epoch.

# %% 6. Thử nhanh 1 câu
FastLanguageModel.for_inference(model)
sample = split["test"][0]["messages"][:-1]          # bỏ câu trả lời mẫu
inputs = tokenizer.apply_chat_template(sample, add_generation_prompt=True, return_tensors="pt").to("cuda")
out = model.generate(input_ids=inputs, max_new_tokens=400, temperature=0.2)
print(tokenizer.decode(out[0][inputs.shape[1]:], skip_special_tokens=True))

# %% 7. Lưu adapter LoRA (nhỏ, để lưu trữ / chạy bằng vLLM)
model.save_pretrained(OUTPUT_NAME)
tokenizer.save_pretrained(OUTPUT_NAME)

# %% 8. Xuất GGUF đã gộp LoRA + lượng tử hoá (để chạy bằng Ollama trên laptop)
model.save_pretrained_gguf(OUTPUT_NAME + "-gguf", tokenizer, quantization_method="q4_k_m")
# Tải thư mục *-gguf về máy (hoặc copy sang Google Drive), rồi làm theo docs/14-finetune.md mục "Đưa model lên web".
