# Tổng quan cho người mới

Đọc file này trước khi đọc hướng dẫn của phần mình. Mất khoảng 20 phút.

## 1. Mình đang làm gì

Một trang web chat. Sinh viên gõ câu hỏi học vụ ("đăng ký học phần bổ sung thế nào?"), chatbot trả lời ngắn gọn và ghi rõ lấy từ văn bản nào của trường.

Để so với HustVA một cách công bằng, nhóm xây một **bộ đề ~200 câu** có đáp án chuẩn, hỏi cả HustVA và chatbot của mình, rồi chấm điểm.

## 2. Ý tưởng cốt lõi: RAG

Model ngôn ngữ (LLM) như Opus 5.5 rất giỏi viết, nhưng **không biết** quy chế mới nhất của HUST, và nếu hỏi thẳng nó có thể bịa. RAG (Retrieval-Augmented Generation) giải quyết bằng cách:

1. **Tìm** trước những đoạn văn bản của trường liên quan đến câu hỏi.
2. **Đưa** các đoạn đó cho model kèm câu hỏi, dặn "chỉ trả lời dựa trên các đoạn này, ghi số nguồn".
3. Model **viết** câu trả lời từ đúng các đoạn đó.

Giống như thi được mở tài liệu: thay vì bắt học thuộc (fine-tune), mình đưa đúng trang sách cho model đọc rồi trả lời.

## 3. Đường đi của một câu hỏi

```
Sinh viên gõ câu hỏi
   │
   ▼
[web/]  app.js gửi POST /api/chat  ───────────────► [backend/app/main.py]
                                                         │ kiểm tra đầu vào
                                                         ▼
                                              [backend/app/rag/pipeline.py]
                                                         │
          ┌──────────────────────────────────────────────┤
          ▼                                              │
  1. viết lại câu hỏi                                    │
  2. retriever.py: tìm đoạn văn bản ◄── Supabase (bảng chunks, do data/ nạp vào)
  3. prompts.py: ghép đoạn văn bản + câu hỏi thành prompt
  4. generators.py: gọi model qua API ──► Anthropic / OpenAI / Ollama(model fine-tune)
          │
          ▼
  câu trả lời chạy về từng chữ (SSE) ──► web/ hiển thị, kèm danh sách nguồn
```

Mỗi phần trong nhóm sở hữu một đoạn của đường đi này. Hợp đồng giữa các đoạn ghi trong [02-api-contract.md](02-api-contract.md).

## 4. Từ điển nhanh

| Thuật ngữ | Nghĩa trong dự án này |
| --- | --- |
| **LLM** | Model ngôn ngữ lớn: Opus 5.5, GPT, Qwen, Llama... |
| **API** | Gọi model qua Internet: gửi văn bản, nhận văn bản, trả tiền theo lượng chữ. |
| **Token** | Đơn vị chữ mà model đếm. Một từ tiếng Việt thường là 1–3 token. Giá API tính theo token. |
| **Prompt** | Toàn bộ chữ gửi cho model: lời dặn (system prompt) + tài liệu + câu hỏi. |
| **Chunk** | Một đoạn văn bản nhỏ (thường là một Điều của quy chế) được cắt ra để tìm kiếm. |
| **Embedding** | Biến một đoạn chữ thành một dãy số (vector, ở đây 1024 số). Hai đoạn nghĩa gần nhau thì dãy số gần nhau. |
| **Vector DB** | CSDL tìm được "đoạn nào có nghĩa gần câu hỏi nhất". Nhóm dùng Supabase (Postgres + pgvector). |
| **Hybrid search** | Tìm theo nghĩa (vector) + tìm theo từ khoá (full-text), rồi gộp kết quả. |
| **Rerank** | Sau khi tìm ra ~20 đoạn, dùng một model nhỏ chấm lại để chọn 5–6 đoạn tốt nhất. |
| **SSE** | Server-Sent Events: backend gửi câu trả lời về từng mẩu, UI hiện dần như đang gõ. |
| **Fine-tune** | Train tiếp một model có sẵn trên dữ liệu của mình để nó quen cách trả lời. |
| **LoRA** | Cách fine-tune rẻ: chỉ train thêm một "miếng vá" vài chục MB gắn lên model gốc. |
| **Distillation** | Model mạnh (teacher) tạo dữ liệu mẫu, model nhỏ (student) học theo. |
| **GGUF** | Định dạng file model đã nén, chạy được trên laptop bằng Ollama/llama.cpp. |
| **Ollama / vLLM** | Phần mềm chạy model trên máy mình và mở ra một API giống hệt API của OpenAI. |
| **LLM-judge** | Dùng model mạnh làm giám khảo chấm câu trả lời theo rubric. |

## 5. Hai phương án sinh câu trả lời

| | Phương án A: API model mạnh | Phương án B: model nhỏ tự fine-tune |
| --- | --- | --- |
| Model | Opus 5.5 hoặc model mạnh khác | Qwen/Llama 3–8B + LoRA của nhóm |
| Train ở đâu | Không cần train | Colab Pro |
| Chạy ở đâu | Máy chủ của nhà cung cấp | MacBook Pro của nhóm, bằng Ollama |
| Backend gọi thế nào | HTTP API | HTTP API (Ollama/vLLM mở API chuẩn OpenAI) |
| Chất lượng | Cao ngay từ đầu | Phải train, thường kém A một chút |
| Chi phí | Trả theo token | Gần như miễn phí khi chạy, tốn công train |
| Khi nào làm | Từ tuần 3 | Thí nghiệm tuần 6–7, không bắt buộc |

**Cả hai đều chạy trong RAG.** Fine-tune không thay việc tìm văn bản; nó chỉ giúp model nhỏ trả lời đúng định dạng, đúng văn phong, biết trích nguồn và biết nói "không biết".

## 6. Hỏi đáp: fine-tune xong thì đưa model vào web thế nào?

Web **không bao giờ** chứa model. Đường đi luôn là:

```
web  ──HTTP──►  backend  ──HTTP──►  "máy chạy model"
```

- Phương án A: "máy chạy model" là máy chủ của Anthropic/OpenAI.
- Phương án B: "máy chạy model" là **Ollama** trên MacBook Pro của nhóm (model được train trên Colab Pro, xuất ra file GGUF rồi chép sang Mac). Hai phần mềm này mở ra một địa chỉ như `http://localhost:11434/v1` nói chuyện **y hệt API của OpenAI**.

Nên backend chỉ cần đổi 3 dòng trong `.env`:

```env
LLM_PROVIDER=openai_compat
OPENAI_BASE_URL=http://localhost:11434/v1
LLM_MODEL=chatbot-hust
```

Code trong `backend/app/rag/generators.py` không đổi. Chi tiết từng bước (xuất GGUF trên Colab → tải về → `ollama create` → trỏ backend vào): [14-finetune.md, mục 5](14-finetune.md#5-đưa-model-fine-tune-lên-web).

## 7. Các model mạnh nhóm đang có dùng vào đâu

| Việc | Ai dùng | File |
| --- | --- | --- |
| Sinh câu trả lời (phương án A) | AI | `.env`: `LLM_PROVIDER`, `LLM_MODEL` |
| Đọc PDF scan, bảng học phí | Data | làm tay, xem [13-data.md](13-data.md) |
| Sinh câu hỏi cho bộ đề | Eval | làm tay hoặc script, xem [15-eval.md](15-eval.md) |
| Teacher sinh dữ liệu fine-tune | Fine-tune | `finetune/make_sft_dataset.py` |
| Giám khảo chấm điểm | Eval | `eval/judge.py` (2 model khác hãng) |
| Viết code | Cả nhóm | Trợ lý lập trình |

Lưu ý: nhiều nhà cung cấp hạn chế dùng output để train model khác. Phần Fine-tune phải đọc điều khoản trước khi chạy teacher.
