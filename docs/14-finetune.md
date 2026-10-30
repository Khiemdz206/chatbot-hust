# Hướng dẫn phần Fine-tune

**Người phụ trách:** TV4 · **Thư mục:** `finetune/` · **Task:** T2 (hỗ trợ), T13, T14

## 1. Bạn làm gì, và không làm gì

Bạn tạo **phương án B**: một model nhỏ (3–8 tỷ tham số) được fine-tune để trả lời giống phương án A nhưng chạy rẻ, chạy được trên máy nhóm.

Hiểu đúng ngay từ đầu:

- Model fine-tune **vẫn chạy trong RAG**. Nó vẫn nhận các đoạn văn bản do retriever tìm ra. Fine-tune dạy nó *cách* trả lời (ngắn, có `[n]`, biết nói "chưa tìm thấy"), không nhồi kiến thức quy chế vào model. Quy chế đổi thì chỉ cần cập nhật dữ liệu, không phải train lại.
- Web **không chứa model**. Model chạy trong Ollama hoặc vLLM, backend gọi nó qua HTTP y như gọi API của OpenAI (mục 5).
- Phương án B là thí nghiệm. Nếu không kịp, demo bằng phương án A và đưa B vào phần "hướng phát triển" của báo cáo.

## 2. Cần học trước (khoảng 8–10 giờ, rải trong tuần 1–3)

| Chủ đề | Đủ để làm gì | Tìm với từ khoá |
| --- | --- | --- |
| LLM, token, chat template | Hiểu dữ liệu train trông thế nào | "chat template huggingface" |
| Fine-tune, SFT, LoRA, QLoRA | Hiểu mình đang train cái gì | "LoRA explained", "QLoRA" |
| Distillation | Hiểu vai trò teacher | "knowledge distillation LLM synthetic data" |
| Unsloth trên Colab | Train thật | "Unsloth notebooks" (chọn notebook đúng dòng model) |
| Overfitting, train/eval loss | Biết khi nào dừng | "train loss vs validation loss" |
| GGUF, lượng tử hoá, Ollama | Chạy model trên máy | "Ollama import GGUF Modelfile" |
| vLLM | Chạy model trên GPU, mở API | "vLLM OpenAI compatible server LoRA" |

## 3. File bạn sở hữu

| File | Nội dung |
| --- | --- |
| `finetune/make_sft_dataset.py` | Teacher sinh câu hỏi + câu trả lời từ chunk thật, lọc, xuất `datasets/sft.jsonl` |
| `finetune/train_lora_colab.py` | Script train trên Colab, chia thành từng ô `# %%` |
| `finetune/serve/Modelfile` | Tạo model trong Ollama từ file GGUF |

Dataset và file model không đưa lên Git. Lưu ở Google Drive nhóm, ghi đường dẫn vào PR.

## 4. Quy trình distillation

```
data/chunks/chunks.jsonl
   │
   ▼  (1) teacher sinh 3–5 câu hỏi kiểu sinh viên cho mỗi chunk
   ▼  (2) dựng ngữ cảnh như lúc chạy thật: chunk đúng + 3 chunk gây nhiễu, xáo trộn
   │      ~15% mẫu bỏ chunk đúng → dạy model nói "chưa tìm thấy"
   ▼  (3) teacher trả lời với ĐÚNG system prompt của backend (rag/prompts.py)
   ▼  (4) lọc: phải có [n]; bỏ câu giống bộ eval; kiểm tay 5%
finetune/datasets/sft.jsonl  ──► Colab: train LoRA ──► adapter + file GGUF ──► Ollama/vLLM ──► backend
```

Bước (3) dùng chung `prompts.py` với backend là điểm mấu chốt: model học đúng định dạng mà nó sẽ gặp khi chạy thật.

## 5. Đưa model fine-tune lên web

### 5.1. Vì sao lại "gọi qua API"

Backend đã có sẵn `OpenAICompatGenerator` trong `backend/app/rag/generators.py`. Nó nói chuyện với bất kỳ máy chủ nào theo chuẩn API của OpenAI. Ollama và vLLM đều mở ra đúng chuẩn đó. Nên:

```
web ──► backend ──HTTP──► Ollama (máy nhóm)  hoặc  vLLM (GPU)  ──► model fine-tune
```

Chỉ đổi `.env`, không sửa code.

### 5.2. Cách 1 (khuyên dùng): Ollama trên máy nhóm

Phù hợp model 3B (vừa GPU 4GB) hoặc 7B 4-bit (chạy được với RAM lớn, chậm hơn).

1. Trên Colab, chạy hết `train_lora_colab.py`, tới ô 8 sẽ có thư mục `chatbot-hust-lora-gguf/` chứa file `.gguf`.
2. Copy thư mục đó sang Google Drive, tải về máy, đặt cạnh `finetune/serve/Modelfile`.
3. Cài Ollama (ollama.com), rồi:
   ```bash
   cd finetune/serve
   # sửa dòng FROM trong Modelfile cho đúng tên file .gguf
   ollama create chatbot-hust -f Modelfile
   ollama run chatbot-hust "Xin chào"
   ```
4. Kiểm tra API chuẩn OpenAI đã mở:
   ```bash
   curl http://localhost:11434/v1/chat/completions -H "Content-Type: application/json" \
     -d '{"model":"chatbot-hust","messages":[{"role":"user","content":"Xin chào"}]}'
   ```
5. Sửa `.env` rồi chạy lại backend:
   ```env
   LLM_PROVIDER=openai_compat
   OPENAI_BASE_URL=http://localhost:11434/v1
   LLM_MODEL=chatbot-hust
   ```
6. Hỏi trên web. `GET /api/health` phải báo `openai_compat` và `chatbot-hust`.

**Khi backend đã deploy lên mạng** (Render, Railway), nó không gọi được `localhost` của laptop. Lúc demo có hai cách: chạy backend ngay trên máy có Ollama, hoặc mở đường hầm (ngrok, Cloudflare Tunnel) cho cổng 11434 rồi đặt `OPENAI_BASE_URL` thành địa chỉ đường hầm. Đường hầm công khai thì phải đặt mật khẩu/token, đừng để ai cũng gọi được.

Nếu câu trả lời bị lặp hoặc lẫn ký tự lạ: Modelfile đang thiếu chat template. Dùng Modelfile mà Unsloth xuất kèm (nếu có), hoặc thêm `TEMPLATE` đúng dòng model.

### 5.3. Cách 2: vLLM trên GPU

Phù hợp khi cần nhanh hoặc nhiều người dùng cùng lúc. Chạy trên Colab/Kaggle được cho demo ngắn (phiên sẽ tắt sau vài giờ), hoặc thuê GPU theo giờ.

```bash
pip install vllm
vllm serve <tên model gốc trên Hugging Face> \
  --enable-lora --lora-modules chatbot-hust=./chatbot-hust-lora \
  --max-model-len 8192 --api-key <mat-khau-tu-dat>
```

vLLM mở API ở cổng 8000 với đường dẫn `/v1`. Trong `.env`: `OPENAI_BASE_URL=http://<dia-chi>:8000/v1`, `OPENAI_API_KEY=<mat-khau-tu-dat>`, `LLM_MODEL=chatbot-hust`.

Cách này dùng **adapter LoRA** (ô 7), không cần file GGUF.

### 5.4. Cách 3: dịch vụ chạy model có sẵn

Một số dịch vụ nhận adapter/model của mình và trả về một API endpoint, trả tiền theo giờ GPU. Tiện nhưng tốn tiền; chỉ cân nhắc nếu nhóm có ngân sách. Cách gọi từ backend vẫn y như trên.

## 6. Việc theo tuần

### Tuần 1–3: học và hỗ trợ
- [ ] Tuần 1: hỗ trợ Eval viết câu hỏi cho bộ đề (bạn sẽ hiểu sinh viên hỏi gì, rất có ích khi sinh dữ liệu).
- [ ] Tuần 2: hỗ trợ Data đọc kiểm văn bản đã làm sạch.
- [ ] Tuần 3: chạy thử `train_lora_colab.py` với **20 mẫu tự viết tay** để chắc mọi ô chạy được, xuất GGUF, chạy được bằng Ollama trên máy. Phát hiện lỗi môi trường sớm.
- [ ] Đọc điều khoản sử dụng của model định làm teacher: có cho dùng output để train model khác không. Không chắc thì chọn teacher open-weight.

**Xong khi:** đi hết được đường Colab → GGUF → Ollama → backend với model đồ chơi.

### Tuần 4–5 – T13: dataset
- [ ] Nhận `data/chunks/chunks.jsonl` từ Data; điền `TEACHER_PROVIDER`, `TEACHER_MODEL` trong `.env`.
- [ ] Chạy thử nhỏ: `python make_sft_dataset.py --n 10`, đọc kỹ từng mẫu.
- [ ] Chạy lớn: mục tiêu ~2.000 mẫu. Ước chi phí trước (số chunk × số câu × độ dài) và báo Lead.
- [ ] Kiểm tay ngẫu nhiên 5% (~100 mẫu): câu trả lời đúng với ngữ cảnh không, trích `[n]` đúng không. Tỉ lệ lỗi > 10% thì sửa prompt teacher và sinh lại.
- [ ] Ghi lại thống kê: số mẫu, % không trả lời được, độ dài trung bình.

**Xong khi:** `sft.jsonl` ~2.000 mẫu, tỉ lệ lỗi kiểm tay ≤ 10%, không trùng bộ eval.

### Tuần 6–7 – T14: train và so sánh
- [ ] Chọn model gốc: bắt đầu với bản 3B (nhanh, vừa GPU nhỏ); còn thời gian thì thử 7–8B.
- [ ] Train 2 epoch, theo dõi train/eval loss. Eval loss tăng lại thì giảm epoch.
- [ ] Chạy model theo mục 5, trỏ backend vào, nhờ Eval chạy `run_eval.py` + `judge.py`.
- [ ] Lập bảng so sánh A vs B: điểm đúng, % trích nguồn, % bịa, độ trễ, chi phí ước tính cho 1.000 câu hỏi.

**Xong khi:** có bảng so sánh A vs B trên cùng bộ đề, Lead chọn được generator cho demo.

## 7. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| Colab hết bộ nhớ GPU (OOM) | Giảm `per_device_train_batch_size` xuống 1, giảm `MAX_SEQ_LEN`, dùng model 3B |
| Colab ngắt giữa chừng | Lưu `outputs/` lên Google Drive; `trainer.train(resume_from_checkpoint=True)` |
| Model trả lời không có `[n]` | Dataset ít mẫu có trích dẫn, hoặc system prompt lúc chạy khác lúc train |
| Model trả lời tốt trên Colab, tệ trên Ollama | Sai chat template trong Modelfile |
| Điểm B thấp hơn A nhiều | Bình thường với model nhỏ. Thử thêm dữ liệu, model lớn hơn, hoặc chấp nhận dùng A |

## 8. Bàn giao

- Nhận từ AI: `prompts.py` ổn định (tuần 4). Prompt đổi sau đó thì phải sinh lại dữ liệu.
- Nhận từ Data: `chunks.jsonl` (tuần 4).
- Giao Lead: model chạy được qua API + bảng so sánh A/B (tuần 7).
