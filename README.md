# Chatbot HUST

Chatbot hỏi đáp học vụ cho sinh viên Đại học Bách khoa Hà Nội. Mục tiêu: trả lời đúng ngang hoặc hơn HustVA trên cùng một bộ câu hỏi, và **luôn chỉ ra nguồn văn bản**.

Nhóm 4 người. Mỗi người làm trong thư mục của mình, mở Pull Request để gộp vào `main`.

> **Vào repo lần đầu:** đọc file hướng dẫn của phần mình (bảng dưới), làm theo từng task. Nếu dùng AI agent, bảo agent đọc [AGENTS.md](AGENTS.md) trước rồi mới đọc file của bạn.

## Ai làm phần nào

| Người | Phần | Thư mục | Đọc file |
| --- | --- | --- | --- |
| Khiêm (Lead) | AI / RAG + Fine-tune | `backend/app/rag/`, `finetune/`, `common/` | [12-ai-rag.md](docs/12-ai-rag.md), [14-finetune.md](docs/14-finetune.md) |
| TV2 | Data | `data/`, `supabase/` | [13-data.md](docs/13-data.md) |
| TV3 | Eval | `eval/` | [15-eval.md](docs/15-eval.md) |
| TV4 | UI + Backend | `web/`, `backend/app/` (trừ `rag/`) | [10-ui.md](docs/10-ui.md), [11-backend.md](docs/11-backend.md) |

Ai cũng nên đọc thêm:

- [docs/01-ke-hoach.md](docs/01-ke-hoach.md): việc của từng người theo tuần, checkpoint.
- [docs/02-api-contract.md](docs/02-api-contract.md): định dạng dữ liệu giữa các phần (API, file JSONL, bảng CSDL).
- [CONTRIBUTING.md](CONTRIBUTING.md): quy trình Git.

## Repo gồm những gì

```
chatbot-hust/
├── web/            UI: giao diện chat (HTML/CSS/JS thuần)
├── backend/app/    Backend: API FastAPI
│   └── rag/        AI: pipeline RAG (tìm văn bản, dựng prompt, gọi model)
├── data/           Data: crawl, làm sạch, chia chunk, đưa lên Supabase
├── supabase/       Cấu trúc CSDL (bảng, hàm tìm kiếm)
├── finetune/       Fine-tune: sinh dữ liệu, train LoRA trên Colab, chạy model bằng Ollama
├── eval/           Eval: bộ câu hỏi vàng, chạy và chấm điểm so với HustVA
├── common/         Hàm gọi model dùng chung cho data/, finetune/, eval/
├── docs/           Hướng dẫn từng phần
└── AGENTS.md       Quy tắc cho AI agent của từng thành viên
```

## Chạy thử trong 5 phút (chế độ mock)

Mock không cần API key hay CSDL: backend trả lời giả và tìm trong vài đoạn văn bản mẫu ở `data/samples/sample_chunks.jsonl`.

Cần: Python 3.10 trở lên, Git.

```bash
git clone https://github.com/<to-chuc>/chatbot-hust.git
cd chatbot-hust
cp .env.example .env              # Windows: copy .env.example .env

cd backend
python -m venv .venv
# macOS/Linux:  source .venv/bin/activate
# Windows:      .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Mở <http://localhost:8000>, bấm một câu hỏi gợi ý: câu trả lời chạy từng chữ, có số `[1]` và danh sách nguồn bên dưới.

Kiểm tra backend: `pytest -q` trong thư mục `backend/` (phải ra `6 passed`).

## Chuyển từ mock sang thật

Chỉ sửa `.env` ở thư mục gốc, không sửa code:

| Muốn | Đặt trong `.env` |
| --- | --- |
| Model mạnh qua API (phương án A) | `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-opus-5-5`, `ANTHROPIC_API_KEY=...` |
| Model nhóm tự fine-tune chạy bằng Ollama (phương án B) | `LLM_PROVIDER=openai_compat`, `OPENAI_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=chatbot-hust` |
| Tìm trong dữ liệu thật | `RETRIEVER=supabase`, `SUPABASE_URL=...`, `SUPABASE_SERVICE_KEY=...` |

Chi tiết phương án B: [docs/14-finetune.md, mục 5](docs/14-finetune.md#5-đưa-model-fine-tune-lên-web).

## Quy tắc chung

- `main` luôn chạy được. Không push thẳng vào `main`.
- Không commit `.env`, API key, dữ liệu crawl, file model.
- Đổi định dạng trong `docs/02-api-contract.md` thì báo cả nhóm và sửa file đó trong cùng PR.
- PR của AI, Data, Fine-tune phải kèm kết quả eval trước/sau.
