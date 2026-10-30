# Chatbot HUST

Chatbot hỏi đáp học vụ cho sinh viên Đại học Bách khoa Hà Nội. Mục tiêu: trả lời đúng ngang hoặc hơn HustVA trên cùng một bộ câu hỏi, và **luôn chỉ ra nguồn văn bản**.

Repo này là chỗ làm việc chung của cả nhóm 5 người. Mỗi người clone về, làm trong thư mục của mình, mở Pull Request để gộp vào `main`.

> Lần đầu vào repo? Đọc theo thứ tự: README này → [docs/00-tong-quan.md](docs/00-tong-quan.md) → hướng dẫn của phần bạn phụ trách.

## Repo gồm những gì

```
chatbot-hust/
├── web/            UI: giao diện chat (HTML/CSS/JS thuần)
├── backend/        Backend: API FastAPI + pipeline RAG (thư mục app/rag/)
├── data/           Data: crawl, làm sạch, chia chunk, đưa lên Supabase
├── supabase/       Cấu trúc CSDL (bảng, hàm tìm kiếm)
├── finetune/       Fine-tune: sinh dữ liệu, train LoRA trên Colab, chạy model
├── eval/           Eval: bộ câu hỏi vàng, chạy và chấm điểm so với HustVA
├── common/         Hàm gọi model dùng chung cho data/finetune/eval
└── docs/           Kế hoạch và hướng dẫn từng phần
```

## Ai làm phần nào

| Phần | Người | Thư mục chính | Hướng dẫn |
| --- | --- | --- | --- |
| Lead / AI (RAG) | Khiêm | `backend/app/rag/` | [12-ai-rag.md](docs/12-ai-rag.md) |
| Data | TV2 | `data/`, `supabase/` | [13-data.md](docs/13-data.md) |
| Eval | TV3 | `eval/` | [15-eval.md](docs/15-eval.md) |
| Fine-tune | TV4 | `finetune/` | [14-finetune.md](docs/14-finetune.md) |
| UI + Backend | TV5 | `web/`, `backend/app/` | [10-ui.md](docs/10-ui.md), [11-backend.md](docs/11-backend.md) |

Kế hoạch 8 tuần: [docs/01-ke-hoach.md](docs/01-ke-hoach.md). Hợp đồng API giữa các phần: [docs/02-api-contract.md](docs/02-api-contract.md). Quy trình Git: [CONTRIBUTING.md](CONTRIBUTING.md).

## Chạy thử trong 5 phút (chế độ mock)

Chế độ mock không cần API key hay CSDL: backend trả lời giả và tìm trong vài đoạn văn bản mẫu. Ai cũng chạy được ngay để hiểu luồng.

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

Mở <http://localhost:8000>, bấm một câu hỏi gợi ý. Bạn sẽ thấy câu trả lời chạy từng chữ, có số `[1]` và danh sách nguồn bên dưới.

Kiểm tra backend: `pytest -q` trong thư mục `backend/` (phải ra 6 passed).

## Chuyển từ mock sang thật

Sửa file `.env` ở thư mục gốc, không cần sửa code:

| Muốn | Đặt trong `.env` |
| --- | --- |
| Dùng model mạnh qua API (phương án A) | `LLM_PROVIDER=anthropic`, `LLM_MODEL=...`, `ANTHROPIC_API_KEY=...` |
| Dùng model nhóm tự fine-tune, chạy bằng Ollama trên Mac (phương án B) | `LLM_PROVIDER=openai_compat`, `OPENAI_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=chatbot-hust` |
| Tìm trong dữ liệu thật | `RETRIEVER=supabase`, `SUPABASE_URL=...`, `SUPABASE_SERVICE_KEY=...` |

Vì sao model fine-tune cũng gọi qua API được: xem [docs/14-finetune.md](docs/14-finetune.md#5-đưa-model-fine-tune-lên-web).

## Quy tắc chung

- `main` luôn chạy được. Không push thẳng vào `main`.
- Không commit `.env`, API key, dữ liệu crawl, file model.
- Đổi hợp đồng API thì báo cả nhóm và sửa `docs/02-api-contract.md` trong cùng PR.
- PR của phần AI, Data, Fine-tune phải kèm kết quả eval trước/sau.
