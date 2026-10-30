# Phần Fine-tune – Khiêm

**Thư mục được sửa:** `finetune/` · **Task:** T13, T14 · Phần RAG của bạn: [12-ai-rag.md](12-ai-rag.md)

Việc của bạn: làm **phương án B**, một model nhỏ (3–8 tỷ tham số) fine-tune bằng LoRA để trả lời giống phương án A nhưng chạy rẻ trên máy của nhóm, rồi so sánh A/B trên cùng bộ đề.

Ba điều cần giữ đúng:

- Model fine-tune **vẫn chạy trong RAG**: vẫn nhận các đoạn văn bản do retriever tìm. Fine-tune dạy *cách* trả lời (ngắn, có `[n]`, biết nói "chưa tìm thấy"), không nhồi quy chế vào model. Quy chế đổi chỉ cần cập nhật dữ liệu, không train lại.
- Web **không chứa model**. Model chạy trong Ollama (hoặc vLLM), backend gọi qua HTTP theo chuẩn OpenAI (mục 5). Chỉ đổi `.env`.
- B là thí nghiệm, làm sau AI (tuần 5–7). Không kịp thì demo bằng A, B vào "hướng phát triển".

## 1. Code hiện có

| File | Nội dung |
| --- | --- |
| `finetune/make_sft_dataset.py` | `--n` (số **chunk** lấy mẫu, mặc định 300), `--per-chunk` (số câu hỏi mỗi chunk, mặc định 4), `--out`, `--seed`. Với mỗi chunk: teacher sinh câu hỏi (`QUESTION_PROMPT`) → bỏ câu giống bộ eval (Jaccard từ > 0.7 so với mọi câu trong `eval/golden/*.jsonl`) → ngữ cảnh = 3 chunk nhiễu + chunk đúng (85%) hoặc chỉ 3 chunk nhiễu (15%), xáo trộn → teacher trả lời với **đúng** `SYSTEM_PROMPT` + `build_messages()` của backend → bỏ mẫu trả lời được mà không có `[n]`. Ghi **nối thêm** (`"a"`) vào `--out`. |
| `finetune/train_lora_colab.py` | Các ô `# %%` dán vào Colab: (1) cấu hình `BASE_MODEL=unsloth/Qwen2.5-7B-Instruct-bnb-4bit`, `MAX_SEQ_LEN=4096` · (2) tải 4-bit · (3) LoRA `r=16` trên mọi lớp attention + MLP · (4) `apply_chat_template`, tách 5% eval · (5) `SFTTrainer` 2 epoch, `lr=2e-4`, batch 2 × accum 4 · (6) thử 1 câu · (7) lưu adapter `chatbot-hust-lora/` · (8) xuất GGUF `q4_k_m` vào `chatbot-hust-lora-gguf/` |
| `finetune/serve/Modelfile` | `FROM ./chatbot-hust-lora-gguf/unsloth.Q4_K_M.gguf`, `temperature 0.2`, `num_ctx 8192` |
| `common/llm.py` | `chat("teacher", ...)` đọc `TEACHER_PROVIDER`, `TEACHER_MODEL` |

Định dạng dataset: [02-api-contract.md mục 10](02-api-contract.md#10-dataset-sft-finetunedatasetssftjsonl). Dataset (`finetune/datasets/`) và model (`*-lora/`, `*.gguf`) không lên Git; lưu Google Drive nhóm, ghi đường dẫn vào PR.

Cài để chạy `make_sft_dataset.py` trên máy:

```bash
cd finetune
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Quy trình

```
data/chunks/chunks.jsonl (TV2)
   │  (1) teacher sinh câu hỏi kiểu sinh viên cho mỗi chunk
   │  (2) dựng ngữ cảnh: chunk đúng + 3 chunk nhiễu; ~15% bỏ chunk đúng → dạy nói "chưa tìm thấy"
   │  (3) teacher trả lời với ĐÚNG prompt của backend (rag/prompts.py)
   │  (4) lọc: có [n]; không trùng bộ eval; kiểm tay 5%
   ▼
finetune/datasets/sft.jsonl ──Colab Pro: train LoRA──► chatbot-hust-lora-gguf/*.gguf ──Ollama trên Mac──► backend (.env)
```

## 3. Task

### T14 bước 0 – Đi thử hết đường với model đồ chơi (tuần 3)

**Mục tiêu:** phát hiện lỗi môi trường sớm, trước khi tốn tiền sinh dữ liệu.

1. Viết tay 20 mẫu đúng định dạng mục 10 của hợp đồng (dùng `build_messages()` để tạo phần `user` cho đúng). Lưu `finetune/datasets/toy.jsonl`.
2. Colab Pro → GPU (L4/A100 nếu còn, T4 cũng được) → `!pip install unsloth` → upload `toy.jsonl`, đặt `DATA_FILE = "toy.jsonl"`, `num_train_epochs=1` → chạy đủ 8 ô.
3. Chép thư mục `chatbot-hust-lora-gguf/` lên Drive; bạn có máy Mac tải về và làm mục 5.2.
4. Trên máy Mac, đo model gốc chưa fine-tune: `ollama run qwen2.5:7b` với một prompt cỡ RAG (dán 6 đoạn quy chế + câu hỏi, ~4.000 token). Ghi thời gian tới chữ đầu tiên và tốc độ (`ollama run --verbose`). Quá 10 giây → chọn model 3B.
5. Đọc điều khoản của nhà cung cấp model định làm teacher: có cho dùng output để train model khác không. Không chắc thì dùng teacher open-weight. Ghi kết luận vào PR.

**Xong khi:** đi hết Colab → GGUF → Ollama → backend (`/api/health` báo `openai_compat`, `chatbot-hust`) với model đồ chơi.

### T13 – Sinh dataset SFT (tuần 4–5)

**Cần trước:** `chunks.jsonl` từ TV2 (đặt vào `data/chunks/`); `SYSTEM_PROMPT` và `format_context()` đã chốt (đổi sau đó là phải sinh lại).

**Sửa script trước khi chạy lớn:**

1. Mẫu **không trả lời được** (`answerable: false`) hiện không bị lọc gì. Thêm điều kiện: câu trả lời phải chứa "chưa tìm thấy" (hoặc cụm tương đương trong quy tắc 3 của prompt) và **không** có `[n]`; không thì bỏ.
2. Script ghi nối thêm vào file: chạy lại sẽ có mẫu trùng. Xoá file cũ trước, hoặc thêm cờ `--overwrite`.
3. Thêm in thống kê cuối: số mẫu, % `answerable: false`, độ dài trung bình câu trả lời.

**Các bước:**

1. `.env`: `TEACHER_PROVIDER`, `TEACHER_MODEL`, key tương ứng.
2. Chạy nhỏ: `python make_sft_dataset.py --n 3 --per-chunk 3 --out datasets/thu.jsonl`. Đọc **từng** mẫu: câu hỏi tự nhiên không, câu trả lời đúng với ngữ cảnh không, `[n]` trỏ đúng đoạn không.
3. Ước chi phí: mỗi chunk = 1 lần gọi sinh câu hỏi + `per-chunk` lần gọi trả lời (mỗi lần ~4.000 token vào, ~300 ra). Với mục tiêu ~2.000 mẫu: `--n 500 --per-chunk 4` ≈ 2.500 lần gọi. Tính theo giá model teacher; quá ngân sách thì giảm `--n` hoặc dùng teacher rẻ hơn.
4. Chạy lớn (chạy nền, mất vài giờ): `python make_sft_dataset.py --n 500 --per-chunk 4`.
5. Kiểm tay ~5% (100 mẫu): viết `finetune/sample_check.py` xuất 100 mẫu ngẫu nhiên ra `datasets/check.md` (câu hỏi, các `[n]` với tiêu đề, câu trả lời, `answerable`). Đánh dấu mẫu lỗi. Tỉ lệ lỗi > 10% → sửa prompt teacher, sinh lại. Có thể nhờ TV2 kiểm một nửa.
6. Kiểm rò bộ eval: lấy 10 câu bất kỳ trong `eval/golden/`, tìm trong `sft.jsonl` (`grep`), không được thấy câu nào gần giống.

**Kiểm tra:** `sft.jsonl` ~2.000 mẫu, 10–20% không trả lời được, lỗi kiểm tay ≤ 10%, không rò bộ eval. PR ghi thống kê + đường dẫn Drive.

### T14 – Train LoRA và so sánh A/B (tuần 6–7)

**Các bước:**

1. Chọn model gốc theo kết quả đo ở bước 0: mặc định `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`; Mac chậm thì `unsloth/Llama-3.2-3B-Instruct-bnb-4bit` (hoặc Qwen 3B). Model gốc trong Colab và trong Ollama phải **cùng dòng** để chat template khớp.
2. Colab: upload `sft.jsonl` (hoặc mount Drive), chạy ô 1–5. Theo dõi `train loss` giảm đều; `eval loss` tăng trở lại → đang overfit, giảm còn 1 epoch.
3. Ô 6: đọc câu trả lời mẫu, phải có `[n]` và ngắn gọn.
4. Ô 7–8, chép `chatbot-hust-lora/` và `chatbot-hust-lora-gguf/` lên Drive (Colab ngắt là mất).
5. Trên Mac: mục 5.2. Backend chạy **trên chính máy Mac**, `RETRIEVER=supabase`, `MIN_SECONDS_BETWEEN_QUESTIONS=0`.
6. Nhờ TV3: `python run_eval.py --golden golden/golden_v2.jsonl --api http://<ip-cua-mac>:8000` rồi `judge.py`. Chạy A trên cùng bộ đề, cùng giám khảo (nếu chưa có).
7. Lập bảng A vs B: điểm đúng, % trích nguồn, % bịa, % từ chối đúng câu ngoài phạm vi, thời gian tới chữ đầu tiên, chi phí ước tính cho 1.000 câu (A: theo giá API; B: ~0, ghi chú cần máy bật).

**Xong khi:** có bảng A/B, chọn generator cho demo ([12-ai-rag.md, tuần 7](12-ai-rag.md#tuần-7--chọn-generator-cho-demo)).

## 4. Học nhanh (nếu cần)

| Chủ đề | Tìm với từ khoá |
| --- | --- |
| Chat template | "chat template huggingface" |
| LoRA, QLoRA | "LoRA explained", "QLoRA" |
| Distillation bằng dữ liệu tổng hợp | "knowledge distillation LLM synthetic data" |
| Unsloth | "Unsloth notebooks" (chọn notebook đúng dòng model) |
| GGUF, Ollama | "Ollama import GGUF Modelfile" |

## 5. Đưa model fine-tune lên web

### 5.1. Vì sao gọi qua API

Backend có sẵn `OpenAICompatGenerator` trong `backend/app/rag/generators.py`, nói chuyện được với mọi máy chủ theo chuẩn API của OpenAI. Ollama và vLLM đều mở đúng chuẩn đó:

```
web ──► backend ──HTTP──► Ollama (máy Mac của nhóm) hoặc vLLM (GPU) ──► model fine-tune
```

Chỉ đổi `.env`, không sửa code.

### 5.2. Ollama trên máy Mac của nhóm

Mac chip M (M1 trở lên) dùng chung RAM cho CPU và GPU nên chạy model 4-bit khá tốt. Laptop GPU 4 GB thì không nên.

| RAM máy Mac | Cỡ model 4-bit (Q4_K_M) chạy thoải mái |
| --- | --- |
| 16 GB | 7–8B (file ~4,5–5 GB), nhưng backend + bge-m3 cũng ăn ~3 GB: cân nhắc 3B |
| 24–36 GB | 7–8B; thử được ~14B |
| 48 GB trở lên | ~14B |

Các bước (trên máy Mac):

1. Cài Ollama (ollama.com, bản macOS). Tải thư mục `chatbot-hust-lora-gguf/` từ Drive, đặt vào `finetune/serve/`.
2. Tạo và thử model:
   ```bash
   cd finetune/serve
   ls chatbot-hust-lora-gguf/          # xem đúng tên file .gguf, sửa dòng FROM trong Modelfile nếu khác
   ollama create chatbot-hust -f Modelfile
   ollama run chatbot-hust "Xin chào"
   ```
   Nếu thư mục xuất của Unsloth có sẵn `Modelfile` (kèm `TEMPLATE`), dùng file đó.
3. Kiểm tra API chuẩn OpenAI:
   ```bash
   curl http://localhost:11434/v1/chat/completions -H "Content-Type: application/json" \
     -d '{"model":"chatbot-hust","messages":[{"role":"user","content":"Xin chào"}]}'
   ```
4. Chạy backend trên máy Mac với `.env`:
   ```env
   LLM_PROVIDER=openai_compat
   OPENAI_BASE_URL=http://localhost:11434/v1
   LLM_MODEL=chatbot-hust
   ```
   `GET /api/health` phải báo `openai_compat` và `chatbot-hust`.

**Cho máy khác trong cùng Wi-Fi gọi tới:** cách đơn giản là để máy khác gọi **backend** trên Mac (`http://<ip-cua-mac>:8000`, chạy uvicorn với `--host 0.0.0.0`). Nếu muốn máy khác gọi thẳng Ollama:

```bash
launchctl setenv OLLAMA_HOST "0.0.0.0"     # rồi tắt hẳn app Ollama và mở lại
```

Máy khác đặt `OPENAI_BASE_URL=http://<ip-cua-mac>:11434/v1`. IP của Mac: *System Settings → Wi-Fi → Details*. Ollama **không có mật khẩu**: chỉ làm vậy trong mạng tin cậy. Wi-Fi trường thường chặn các máy nói chuyện với nhau, khi đó dùng hotspot điện thoại.

**Khi demo cho người ngoài:** không đưa Ollama ra Internet. Chạy backend trên Mac (gọi `localhost:11434`), chỉ mở backend ra ngoài bằng Cloudflare Tunnel hoặc ngrok. Mac phải bật và không ngủ (`caffeinate -i` trong Terminal).

Câu trả lời bị lặp hoặc có ký tự lạ: Modelfile thiếu hoặc sai chat template.

### 5.3. vLLM trên GPU (không bắt buộc)

vLLM cần GPU NVIDIA, **không chạy trên Mac**. Chỉ cân nhắc khi cần nhiều người dùng cùng lúc (Colab Pro cho demo ngắn, hoặc thuê GPU theo giờ). Dùng adapter LoRA (ô 7), không cần GGUF:

```bash
pip install vllm
vllm serve <tên model gốc trên Hugging Face> \
  --enable-lora --lora-modules chatbot-hust=./chatbot-hust-lora \
  --max-model-len 8192 --api-key <mat-khau-tu-dat>
```

`.env`: `OPENAI_BASE_URL=http://<dia-chi>:8000/v1`, `OPENAI_API_KEY=<mat-khau-tu-dat>`, `LLM_MODEL=chatbot-hust`.

## 6. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| `make_sft_dataset.py` báo `FileNotFoundError ... chunks.jsonl` | Chưa đặt file của TV2 vào `data/chunks/chunks.jsonl` |
| `make_sft_dataset.py` báo `Chưa đặt TEACHER_MODEL` | Thiếu biến trong `.env` |
| Nhiều dòng `bỏ chunk ...: JSON` | Teacher không trả đúng JSON; đổi model teacher hoặc nói rõ hơn trong `QUESTION_PROMPT` |
| Colab hết bộ nhớ GPU (OOM) | GPU lớn hơn, hoặc giảm `per_device_train_batch_size`, `MAX_SEQ_LEN` |
| Colab ngắt giữa chừng | Đặt `output_dir` trên Drive; `trainer.train(resume_from_checkpoint=True)` |
| Hàm Unsloth/TRL báo sai tham số | Thư viện đổi nhanh; đối chiếu notebook mẫu mới nhất của Unsloth (vd. `tokenizer=` → `processing_class=`) |
| Model trả lời không có `[n]` | Dataset ít mẫu có trích dẫn, hoặc prompt lúc chạy khác lúc train (đã đổi `prompts.py` sau khi sinh dữ liệu?) |
| Tốt trên Colab, tệ trên Ollama | Sai chat template trong Modelfile |
| Máy khác không gọi được Mac | Chưa `--host 0.0.0.0` / `OLLAMA_HOST`; tường lửa macOS; Wi-Fi trường chặn (dùng hotspot) |
| Mac rất chậm, nóng | Model quá lớn so với RAM; giảm cỡ model hoặc `num_ctx` |
| Điểm B thấp hơn A nhiều | Bình thường với model nhỏ. Thêm dữ liệu, model lớn hơn, hoặc chấp nhận dùng A |
