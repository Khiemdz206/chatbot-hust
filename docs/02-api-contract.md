# Hợp đồng API

Đây là "luật chơi" giữa UI, Backend, AI và Eval. Ai cũng code theo file này nên làm song song được. **Muốn đổi: mở PR sửa file này trước, cả nhóm đồng ý rồi mới sửa code.**

Code tương ứng: `backend/app/schemas.py`, `backend/app/main.py`, `web/app.js`.

## 1. `POST /api/chat`

### Request

```json
{
  "message": "Đăng ký học phần bổ sung thế nào?",
  "session_id": "3f6c...-uuid-luu-o-trinh-duyet",
  "history": [
    {"role": "user", "content": "câu hỏi trước"},
    {"role": "assistant", "content": "câu trả lời trước"}
  ]
}
```

| Trường | Bắt buộc | Ràng buộc |
| --- | --- | --- |
| `message` | có | 1–1000 ký tự |
| `session_id` | không | ≤ 100 ký tự; dùng để giới hạn tần suất và gom log |
| `history` | không | tối đa 12 phần tử; UI gửi 6 phần tử gần nhất |

### Response mặc định: stream (SSE, `text/event-stream`)

Các sự kiện đến **theo đúng thứ tự** này:

```text
event: token
data: {"text": "Theo hướng dẫn "}

event: token
data: {"text": "đăng ký học tập [1]..."}

event: sources
data: [{"n": 1, "title": "Quy chế đào tạo", "section": "Chương II – Điều 12", "url": "https://...", "effective_date": "2025-08-01"}]

event: done
data: {"answer_id": "uuid", "refused": false, "latency_ms": 2140}
```

- `token`: nhiều lần, nối lại thành câu trả lời.
- `sources`: một lần. `n` khớp với số `[n]` trong câu trả lời. Có thể là mảng rỗng.
- `done`: một lần, cuối cùng. `answer_id` dùng cho feedback. `refused: true` nghĩa là chatbot từ chối (không tìm thấy hoặc ngoài phạm vi).
- `error`: thay cho `done` khi có lỗi giữa chừng: `{"code": "UPSTREAM_ERROR", "message": "..."}`.

### Response không stream: `POST /api/chat?stream=false`

Script eval dùng cách này.

```json
{
  "answer_id": "uuid",
  "answer": "Theo hướng dẫn ... [1]",
  "sources": [{"n": 1, "title": "...", "section": "...", "url": "...", "effective_date": "..."}],
  "refused": false,
  "latency_ms": 2140
}
```

## 2. `POST /api/feedback`

```json
{"answer_id": "uuid", "rating": 1, "comment": "tuỳ chọn"}
```

`rating`: `1` (đúng) hoặc `-1` (sai). Trả `{"ok": true}`.

## 3. `GET /api/health`

```json
{"status": "ok", "llm_provider": "anthropic", "llm_model": "claude-opus-5-5", "retriever": "supabase"}
```

Dùng để kiểm tra nhanh backend đang chạy với cấu hình nào.

## 4. `POST /admin/reindex`

Header `X-Admin-Token: <ADMIN_TOKEN trong .env>`. Kích hoạt nạp lại dữ liệu (task T9, chưa cài).

## 5. Mã lỗi

| HTTP | `code` | Khi nào | UI hiển thị |
| --- | --- | --- | --- |
| 422 | (lỗi validate của FastAPI) | `message` rỗng hoặc quá dài | "Câu hỏi không hợp lệ" |
| 429 | `RATE_LIMITED` | Hỏi liên tục trong < 2 giây | "Chờ vài giây rồi hỏi lại" |
| 502 / sự kiện `error` | `UPSTREAM_ERROR` | Model hoặc CSDL lỗi | Thông báo + nút "Thử lại" |

## 6. Hợp đồng bên trong backend (giữa BE và AI)

Backend chỉ gọi đúng một hàm:

```python
from app.rag import pipeline
async for ev in pipeline.answer(question: str, history: list[dict]):
    # ev["type"] là "token" | "sources" | "meta"
```

AI được thay đổi mọi thứ bên trong `backend/app/rag/` miễn giữ đúng hàm này.
