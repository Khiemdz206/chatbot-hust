# Hướng dẫn cho AI agent làm việc trong repo này

File này dành cho AI agent (trợ lý AI lập trình) mà mỗi thành viên dùng. Đọc hết file này trước khi làm bất cứ việc gì.

## 1. Bạn đang giúp ai

Nhóm có 4 người. Mỗi người sở hữu một phần và một file hướng dẫn riêng. **Nếu người dùng chưa nói họ là ai hoặc làm task nào, hãy hỏi trước.**

| Người | Phần | File hướng dẫn phải đọc | Được sửa | Không được sửa (trừ khi người dùng bảo rõ) |
| --- | --- | --- | --- | --- |
| Khiêm (Lead) | AI / RAG + Fine-tune | [docs/12-ai-rag.md](docs/12-ai-rag.md), [docs/14-finetune.md](docs/14-finetune.md) | `backend/app/rag/`, `finetune/`; thêm biến AI vào `backend/app/config.py` + `.env.example`; file mới trong `supabase/migrations/` (báo TV2, TV4) | `web/`, `backend/app/main.py`, `backend/app/store.py`, `data/` |
| TV2 | Data | [docs/13-data.md](docs/13-data.md) | `data/`, `supabase/migrations/` (thêm file mới) | `backend/`, `web/`, `eval/` |
| TV3 | Eval | [docs/15-eval.md](docs/15-eval.md) | `eval/` | mọi thứ ngoài `eval/` |
| TV4 | UI + Backend | [docs/10-ui.md](docs/10-ui.md), [docs/11-backend.md](docs/11-backend.md) | `web/`, `backend/app/` **trừ** `backend/app/rag/`, `backend/tests/`, `supabase/migrations/` (thêm file mới), `.env.example` | `backend/app/rag/`, `data/`, `eval/`, `finetune/` |

Luôn đọc thêm [docs/02-api-contract.md](docs/02-api-contract.md): định dạng dữ liệu đi giữa các phần. Mọi code bạn viết phải khớp file đó.

## 2. Quy tắc bắt buộc

1. **Chỉ sửa file trong phạm vi của người dùng** (bảng trên). Cần đổi file của người khác thì dừng lại, viết rõ cần đổi gì và vì sao để người dùng nhắn cho chủ file.
2. **Không đổi hợp đồng** trong `docs/02-api-contract.md` (tên trường, kiểu dữ liệu, tên sự kiện SSE, tên hàm `pipeline.answer`) nếu người dùng không bảo. Nếu được bảo đổi, sửa `docs/02-api-contract.md` trong cùng PR.
3. **Không commit**: `.env`, key Supabase, `data/raw/`, `data/clean/`, `data/chunks/`, `finetune/datasets/`, file model (`.gguf`, thư mục `*-lora`), `eval/results/`. Đã có trong `.gitignore`, đừng sửa `.gitignore` để bỏ qua.
4. **Không push thẳng vào `main`.** Tạo nhánh theo [CONTRIBUTING.md](CONTRIBUTING.md), commit, rồi để người dùng tự mở PR (hoặc dùng `gh pr create` nếu họ bảo).
5. **Không bịa nội dung quy chế của trường.** Mọi số liệu, điều kiện học vụ phải lấy từ văn bản gốc mà người dùng đưa hoặc đã có trong `data/`.
6. **Không viết script tự động hỏi HustVA** hoặc crawl mạnh trang của trường. Thu đáp án HustVA là việc làm tay.
7. Viết code giống code xung quanh: tiếng Việt có dấu trong comment và thông báo, Python 3.10+, không thêm thư viện mới nếu không cần (thêm thì ghi vào `requirements.txt` của thư mục đó).
8. Trước khi báo xong: chạy lệnh kiểm tra ghi trong mục "Kiểm tra" của task. Báo đúng kết quả, kể cả khi lỗi.

## 3. Lệnh dùng chung

Chạy mọi thứ ở chế độ mock (không cần key, không cần CSDL):

```bash
cp .env.example .env               # một lần, ở thư mục gốc repo
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000    # mở http://localhost:8000
pytest -q                          # phải ra: 6 passed
```

- File `.env` nằm ở **thư mục gốc repo**, mọi script (`backend/`, `data/`, `eval/`, `finetune/`) đều đọc file này.
- Đổi `.env` thì phải tắt và chạy lại uvicorn.
- `backend/app/config.py` là nơi duy nhất đọc biến môi trường của backend. Thêm biến mới: thêm vào `config.py` **và** `.env.example`.

Nhóm **không dùng API model trả tiền**. Chatbot chạy bằng Ollama (`LLM_PROVIDER=ollama`). Đừng thêm code gọi API của OpenAI, Anthropic hay dịch vụ tương tự.

## 4. Bạn có thể được giao làm "teacher" hoặc "giám khảo"

Ai trong nhóm cũng có thể nhờ bạn làm hai việc này, kể cả khi không phải phần của họ:

- **Sinh dữ liệu fine-tune:** người dùng giao một file lô trong `finetune/datasets/q_tasks/` hoặc `a_tasks/`. Đọc [finetune/TEACHER.md](finetune/TEACHER.md) và làm đúng lô đó.
- **Chấm điểm eval:** người dùng giao một file `eval/results/*.judge_tasks.jsonl`. Đọc [eval/RUBRIC.md](eval/RUBRIC.md) và chấm đúng các dòng được giao. Không mở `*.judge_key.json` hay file kết quả gốc.

## 5. Cách làm một task

1. Mở file hướng dẫn của người dùng, tìm task theo mã (vd. `T7`). Mỗi task có: Mục tiêu, Hiện trạng code, Các bước, Kiểm tra, Bàn giao.
2. Đọc các file trong mục "Hiện trạng code" trước khi sửa.
3. Làm theo các bước. Bước nào cần người làm tay (đọc kiểm văn bản, hỏi HustVA, tạo tài khoản, chạy Colab) thì liệt kê ra cho người dùng, đừng giả là đã làm.
4. Chạy phần "Kiểm tra". Nếu task ảnh hưởng chất lượng câu trả lời (AI, Data, Fine-tune), nhắc người dùng nhờ Eval chạy lại eval và dán số trước/sau vào PR.
5. Gợi ý commit message dạng `<Phần>: <việc đã làm>`, vd. `Data: crawl và làm sạch quy chế đào tạo`.

Câu mở đầu gợi ý cho người dùng gõ vào agent:

> Tôi là TV2 (Data). Đọc AGENTS.md và docs/13-data.md, rồi làm task T4 cùng tôi.
