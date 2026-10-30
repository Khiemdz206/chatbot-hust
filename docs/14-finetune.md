# Phần Fine-tune – Khiêm

**Thư mục được sửa:** `finetune/` · **Task:** T13, T14 · Phần RAG của bạn: [12-ai-rag.md](12-ai-rag.md)

Nhóm **không dùng API model trả tiền**. Chatbot trả lời bằng một model nhỏ (3–8 tỷ tham số) nhóm tự fine-tune bằng LoRA, chạy local bằng Ollama trên máy Mac. Phần này là phần chính của dự án, không phải thí nghiệm.

Ba điều cần giữ đúng:

- Model fine-tune **chạy trong RAG**: nó nhận các đoạn văn bản do retriever tìm. Fine-tune dạy *cách* trả lời (ngắn, có `[n]`, biết nói "chưa tìm thấy"), không nhồi quy chế vào model. Quy chế đổi chỉ cần cập nhật dữ liệu, không train lại.
- Web **không chứa model**. Model chạy trong Ollama, backend gọi qua HTTP (API chuẩn OpenAI mà Ollama mở ra). Đổi model chỉ cần đổi `LLM_MODEL` trong `.env`.
- Trước khi có model fine-tune, chatbot chạy bằng **model gốc** (vd. `qwen2.5:7b`) qua Ollama. Đó là mốc so sánh: fine-tune phải làm điểm eval tăng so với model gốc.

"Teacher" (bên viết dữ liệu mẫu cho model nhỏ học) là **AI agent của các thành viên**, không gọi API. Script chỉ chia việc thành lô và gom kết quả.

## 1. Code hiện có

| File | Nội dung |
| --- | --- |
| `finetune/make_sft_dataset.py` | 3 bước: `questions --n N` (lấy N chunk, chia lô 20 cho agent viết câu hỏi) → `contexts` (bỏ câu giống bộ eval, dựng ngữ cảnh bằng đúng `build_messages()` của backend: chunk đúng + 3 chunk nhiễu, 15% bỏ chunk đúng; chia lô 20 cho agent viết câu trả lời) → `build` (lọc, ghi `datasets/sft.jsonl`, in thống kê) |
| `finetune/TEACHER.md` | Hướng dẫn cho agent: viết câu hỏi thế nào, trả lời thế nào (đóng vai đúng `SYSTEM_PROMPT`), định dạng file ra |
| `finetune/train_lora_colab.py` | Các ô `# %%` dán vào Colab: (1) cấu hình `BASE_MODEL=unsloth/Qwen2.5-7B-Instruct-bnb-4bit`, `MAX_SEQ_LEN=4096` · (2) tải 4-bit · (3) LoRA `r=16` · (4) `apply_chat_template`, tách 5% eval · (5) `SFTTrainer` 2 epoch, `lr=2e-4` · (6) thử 1 câu · (7) lưu adapter `chatbot-hust-lora/` · (8) xuất GGUF `q4_k_m` vào `chatbot-hust-lora-gguf/` |
| `finetune/serve/Modelfile` | `FROM ./chatbot-hust-lora-gguf/unsloth.Q4_K_M.gguf`, `temperature 0.2`, `num_ctx 8192` |

Bộ lọc ở bước `build`: mẫu trả lời được phải có `[n]`; mẫu không trả lời được phải chứa "chưa tìm thấy" và không có `[n]`.

Định dạng dataset: [02-api-contract.md mục 10](02-api-contract.md#10-dataset-sft-finetunedatasetssftjsonl). `finetune/datasets/` và model (`*-lora/`, `*.gguf`) không lên Git; lưu Google Drive nhóm.

Chạy script (dùng chung venv của backend, không cần cài thêm):

```bash
cd finetune
../backend/.venv/bin/python make_sft_dataset.py --help    # Windows: ..\backend\.venv\Scripts\python
```

## 2. Quy trình

```
data/chunks/chunks.jsonl (TV2)
   │  make_sft_dataset.py questions  ──► q_tasks/batch_XXX.jsonl ──agent──► batch_XXX.out.jsonl (câu hỏi)
   │  make_sft_dataset.py contexts   ──► a_tasks/batch_XXX.jsonl ──agent──► batch_XXX.out.jsonl (câu trả lời)
   │  make_sft_dataset.py build      ──► sft.jsonl + thống kê; người kiểm tay 5%
   ▼
Colab Pro: train LoRA ──► chatbot-hust-lora-gguf/*.gguf ──► Ollama trên Mac ──► backend (LLM_MODEL=chatbot-hust)
```

## 3. Task

### Tuần 1 – Chọn model và máy chạy

1. Trên máy Mac của nhóm: cài Ollama (ollama.com), `ollama pull qwen2.5:7b`, `ollama pull qwen2.5:3b`.
2. Đo với một prompt cỡ RAG (6 đoạn quy chế + câu hỏi, ~4.000 token): `ollama run qwen2.5:7b --verbose`. Ghi thời gian tới chữ đầu tiên và tốc độ (token/giây). Mục tiêu < 3 giây tới chữ đầu tiên; quá 10 giây thì chọn 3B.
3. Cộng RAM: model (7B 4-bit ~5 GB, 3B ~2 GB) + model embedding bge-m3 (~2,5 GB) + reranker nếu dùng (~2 GB) + hệ điều hành. Mac 16 GB nên dùng 3B.
4. Chốt model gốc, ghi vào PR. Gửi TV4 tên model để đặt `LLM_MODEL`.

### T14 bước 0 – Đi thử hết đường với model đồ chơi (tuần 3)

**Mục tiêu:** phát hiện lỗi môi trường sớm.

1. Bảo agent viết 20 mẫu theo `finetune/TEACHER.md` từ `data/samples/sample_chunks.jsonl` (hoặc chạy cả 3 bước của `make_sft_dataset.py` với một `chunks.jsonl` nhỏ). Được `datasets/sft.jsonl` 20 dòng.
2. Colab Pro → GPU (L4/A100 nếu còn, T4 cũng được) → `!pip install unsloth` → upload `sft.jsonl`, `num_train_epochs=1` → chạy đủ 8 ô. `BASE_MODEL` phải cùng dòng với model đã chốt ở tuần 1.
3. Chép `chatbot-hust-lora-gguf/` lên Drive, tải về Mac, làm mục 5.

**Xong khi:** đi hết Colab → GGUF → Ollama → backend (`/api/health` báo `ollama`, `chatbot-hust`) với model đồ chơi.

### T13 – Sinh dataset SFT (tuần 4–5)

**Cần trước:** `chunks.jsonl` từ TV2 (đặt vào `data/chunks/`); `SYSTEM_PROMPT` và `format_context()` đã chốt (đổi sau đó là phải sinh lại).

**Về hạn mức của gói AI:** mỗi câu trả lời agent phải đọc ~4.000 token ngữ cảnh. Một người làm hết sẽ chạm hạn mức nhiều lần. Vì vậy:
- Mục tiêu ~1.000 mẫu (thay vì vài nghìn): `--n 250` chunk × 4 câu hỏi.
- **Chia lô cho cả 4 người**, mỗi người cho agent của mình làm vài lô mỗi ngày. Lô nằm trên Drive, ai làm lô nào ghi vào một bảng chung.
- Mỗi lần nhắn agent chỉ giao 1 lô (20 việc) để nó làm cẩn thận.

**Về điều khoản:** điều khoản của các nhà cung cấp AI thường hạn chế dùng output để train model khác. Đây là dự án môn học với model nội bộ, nhưng nhóm vẫn phải tự đọc điều khoản của gói đang dùng và hỏi giảng viên trước khi làm. Ghi kết luận vào PR.

**Các bước:**

1. `python make_sft_dataset.py questions --n 250` → khoảng 13 lô trong `datasets/q_tasks/`.
2. Với mỗi lô, nhắn agent: *"Đọc finetune/TEACHER.md, làm lô finetune/datasets/q_tasks/batch_001.jsonl"*. Đọc lướt câu hỏi của lô đầu tiên: tự nhiên không, có hỏi điều đoạn văn không nói tới không. Chưa ổn thì sửa `TEACHER.md` trước khi làm tiếp.
3. Làm xong mọi lô câu hỏi: `python make_sft_dataset.py contexts` → khoảng 50 lô trong `datasets/a_tasks/`. Lưu ý: chạy lại bước này sẽ dựng ngữ cảnh mới và **xoá lô cũ chưa làm**, chỉ giữ các file `.out.jsonl`; chạy một lần duy nhất rồi mới chia lô.
4. Chia các lô trả lời cho 4 người. Nhắn agent: *"Đọc finetune/TEACHER.md, làm lô finetune/datasets/a_tasks/batch_001.jsonl"*.
5. Gom mọi file `.out.jsonl` vào `datasets/a_tasks/`, chạy `python make_sft_dataset.py build`. Xem thống kê: 10–20% mẫu không trả lời được; số mẫu bị bỏ thấp.
6. Kiểm tay ~5% (50 mẫu): mở `sft.jsonl`, đọc ngẫu nhiên. Câu trả lời đúng với ngữ cảnh không, `[n]` trỏ đúng đoạn không. Lỗi > 10% → sửa `TEACHER.md`, làm lại các lô đó.
7. Kiểm rò bộ eval: lấy 10 câu bất kỳ trong `eval/golden/`, tìm trong `sft.jsonl`, không được thấy câu nào gần giống.

**Kiểm tra:** `sft.jsonl` ~1.000 mẫu, lỗi kiểm tay ≤ 10%, không rò bộ eval. PR ghi thống kê + đường dẫn Drive.

### T14 – Train LoRA và so sánh với model gốc (tuần 5–6)

**Các bước:**

1. Colab: upload `sft.jsonl` (hoặc mount Drive), chạy ô 1–5. `train loss` phải giảm đều; `eval loss` tăng trở lại → overfit, giảm còn 1 epoch.
2. Ô 6: đọc câu trả lời mẫu, phải có `[n]` và ngắn gọn.
3. Ô 7–8, chép `chatbot-hust-lora/` và `chatbot-hust-lora-gguf/` lên Drive ngay (Colab ngắt là mất).
4. Trên Mac: mục 5. Backend chạy trên Mac với `LLM_MODEL=chatbot-hust`.
5. Nhờ TV3 chạy eval trên cùng bộ đề cho **model gốc** và **model fine-tune**. Lập bảng: điểm đúng, % trích nguồn, % bịa, % từ chối đúng câu ngoài phạm vi, thời gian tới chữ đầu tiên.
6. Fine-tune không hơn model gốc → xem câu sai, bổ sung dữ liệu đúng kiểu đó, train lại (v2). Tuần 6 có thời gian cho một vòng nữa.

**Xong khi:** có bảng model gốc vs fine-tune; chọn bản tốt nhất cho demo và ghi tên vào `.env` của máy demo.

## 4. Học nhanh (nếu cần)

| Chủ đề | Tìm với từ khoá |
| --- | --- |
| Chat template | "chat template huggingface" |
| LoRA, QLoRA | "LoRA explained", "QLoRA" |
| Distillation bằng dữ liệu tổng hợp | "knowledge distillation LLM synthetic data" |
| Unsloth | "Unsloth notebooks" (chọn notebook đúng dòng model) |
| GGUF, Ollama | "Ollama import GGUF Modelfile" |

## 5. Đưa model fine-tune lên web

### 5.1. Backend gọi Ollama thế nào

`OllamaGenerator` trong `backend/app/rag/generators.py` gọi Ollama qua API chuẩn OpenAI tại `LLM_BASE_URL`:

```
web ──► backend ──HTTP──► Ollama (máy Mac của nhóm) ──► model gốc hoặc model fine-tune
```

### 5.2. Ollama trên máy Mac của nhóm

1. Tải thư mục `chatbot-hust-lora-gguf/` từ Drive, đặt vào `finetune/serve/`.
2. Tạo và thử model:
   ```bash
   cd finetune/serve
   ls chatbot-hust-lora-gguf/          # xem đúng tên file .gguf, sửa dòng FROM trong Modelfile nếu khác
   ollama create chatbot-hust -f Modelfile
   ollama run chatbot-hust "Xin chào"
   ```
   Nếu thư mục xuất của Unsloth có sẵn `Modelfile` (kèm `TEMPLATE`), dùng file đó.
3. Kiểm tra API:
   ```bash
   curl http://localhost:11434/v1/chat/completions -H "Content-Type: application/json" \
     -d '{"model":"chatbot-hust","messages":[{"role":"user","content":"Xin chào"}]}'
   ```
4. `.env` của backend trên Mac:
   ```env
   LLM_PROVIDER=ollama
   LLM_BASE_URL=http://localhost:11434/v1
   LLM_MODEL=chatbot-hust
   ```
   `GET /api/health` phải báo `ollama` và `chatbot-hust`.

**Cho máy khác trong cùng Wi-Fi dùng** (vd. TV3 chạy eval, TV4 dev UI): cách đơn giản là gọi **backend** trên Mac (`http://<ip-cua-mac>:8000`, chạy uvicorn với `--host 0.0.0.0`). Nếu một người muốn chạy backend trên máy mình nhưng dùng Ollama của Mac:

```bash
launchctl setenv OLLAMA_HOST "0.0.0.0"     # trên Mac, rồi tắt hẳn app Ollama và mở lại
```

Máy kia đặt `LLM_BASE_URL=http://<ip-cua-mac>:11434/v1`. IP của Mac: *System Settings → Wi-Fi → Details*. Ollama **không có mật khẩu**: chỉ làm vậy trong mạng tin cậy. Wi-Fi trường thường chặn các máy nói chuyện với nhau, khi đó dùng hotspot điện thoại.

**Khi mở cho người ngoài:** không đưa Ollama ra Internet. TV4 mở backend ra ngoài bằng Cloudflare Tunnel ([11-backend.md, T16a](11-backend.md#t16a--mở-công-khai-tuần-7)). Mac phải bật và không ngủ (`caffeinate -i`).

Câu trả lời bị lặp hoặc có ký tự lạ: Modelfile thiếu hoặc sai chat template.

## 6. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| `UnicodeEncodeError: 'charmap'` khi chạy script trên Windows | Console không in được tiếng Việt: `set PYTHONUTF8=1` (cmd) hoặc `$env:PYTHONUTF8=1` (PowerShell) trước khi chạy |
| `FileNotFoundError ... chunks.jsonl` | Chưa đặt file của TV2 vào `data/chunks/chunks.jsonl` |
| `ModuleNotFoundError: dotenv` | Chạy bằng python của venv backend (mục 1) |
| `build` báo nhiều mẫu "thiếu [n]" | Agent quên trích dẫn; nhắc lại quy tắc 2 trong `TEACHER.md`, làm lại lô đó |
| Agent báo hết hạn mức | Chờ hạn mức hồi lại, hoặc chuyển lô cho người khác |
| Colab hết bộ nhớ GPU (OOM) | GPU lớn hơn, hoặc giảm `per_device_train_batch_size`, `MAX_SEQ_LEN` |
| Colab ngắt giữa chừng | Đặt `output_dir` trên Drive; `trainer.train(resume_from_checkpoint=True)` |
| Hàm Unsloth/TRL báo sai tham số | Thư viện đổi nhanh; đối chiếu notebook mẫu mới nhất của Unsloth (vd. `tokenizer=` → `processing_class=`) |
| Model trả lời không có `[n]` | Dataset ít mẫu có trích dẫn, hoặc prompt lúc chạy khác lúc train (đã đổi `prompts.py` sau khi sinh dữ liệu?) |
| Tốt trên Colab, tệ trên Ollama | Sai chat template trong Modelfile |
| Máy khác không gọi được Mac | Chưa `--host 0.0.0.0` / `OLLAMA_HOST`; tường lửa macOS; Wi-Fi trường chặn (dùng hotspot) |
| Mac rất chậm, nóng | Model quá lớn so với RAM; giảm cỡ model hoặc `num_ctx` |
