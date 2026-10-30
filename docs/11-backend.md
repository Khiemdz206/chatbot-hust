# Hướng dẫn phần Backend

**Người phụ trách:** TV5, phối hợp Khiêm ở chỗ nối với AI · **Thư mục:** `backend/app/` (trừ `rag/`), `supabase/` · **Task:** T3, T7, T12, T16, T19

## 1. Bạn làm gì

Backend là lớp mỏng nằm giữa UI và AI: nhận câu hỏi, kiểm tra, gọi `pipeline.answer()`, đẩy kết quả về UI theo từng chữ, ghi log. **Không viết logic AI ở đây**, để Khiêm đổi model/cách tìm kiếm mà không phải sửa API.

## 2. Cần học trước (khoảng 6–8 giờ)

| Chủ đề | Đủ để làm gì | Tìm với từ khoá |
| --- | --- | --- |
| Python cơ bản, `venv`, `pip` | Cài và chạy dự án | "python venv tutorial" |
| FastAPI | Viết endpoint, đọc request | "FastAPI tutorial first steps" (tài liệu chính thức rất dễ đọc) |
| Pydantic | Kiểm tra dữ liệu vào | "FastAPI request body" |
| `async`/`await`, async generator | Stream câu trả lời | "python async generator", "FastAPI StreamingResponse" |
| SSE | Định dạng `event:`/`data:` | "Server-Sent Events format" |
| Supabase Python | Ghi log vào bảng | "supabase python insert" |
| pytest | Viết test | "FastAPI testing" |

## 3. File bạn sở hữu

| File | Nội dung |
| --- | --- |
| `backend/app/main.py` | Các endpoint, SSE, giới hạn tần suất, phục vụ `web/` |
| `backend/app/schemas.py` | Kiểu dữ liệu vào/ra, khớp hợp đồng API |
| `backend/app/store.py` | Ghi `chat_logs`, `feedback` (Supabase hoặc file) |
| `backend/app/config.py` | Đọc `.env` (dùng chung với AI) |
| `backend/tests/` | Test |
| `supabase/migrations/` | Cấu trúc CSDL (làm cùng Data) |

## 4. Chạy thử ngay

```bash
cd backend
source .venv/bin/activate          # Windows: .venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
pytest -q                          # ở terminal khác
```

Mở <http://localhost:8000/docs>: FastAPI tự sinh trang thử API. Bấm `POST /api/chat` → *Try it out*.

Thử stream bằng terminal:

```bash
curl -N -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"Học phí tính theo tín chỉ ra sao?"}'
```

## 5. Luồng xử lý `/api/chat` (đã có sẵn khung trong `main.py`)

1. **Kiểm tra đầu vào:** Pydantic tự trả 422 nếu `message` rỗng hoặc > 1000 ký tự.
2. **Giới hạn tần suất:** mỗi `session_id` cách nhau ≥ 2 giây, sai thì 429.
3. **Gọi pipeline:** `pipeline.answer(message, history)` trả về lần lượt `token`, `sources`, `meta`.
4. **Stream về UI:** đổi thành sự kiện SSE `token` → `sources` → `done`.
5. **Ghi log nền:** `asyncio.create_task(store.log_chat(row))` để không làm chậm câu trả lời.
6. **Có lỗi giữa chừng:** gửi sự kiện `error` thay vì làm đứt kết nối.

## 6. Việc theo tuần

### Tuần 1 – T3
- [ ] Chạy mock, chạy `pytest`, đọc hiểu `main.py`.
- [ ] Tạo project Supabase (gói miễn phí), mời cả nhóm vào.
- [ ] Mở **SQL Editor**, dán `supabase/migrations/001_init.sql`, chạy. Kiểm tra có 4 bảng trong **Table Editor**.
- [ ] Gửi `SUPABASE_URL` và `service_role key` cho nhóm **qua tin nhắn riêng**, không đưa lên Git.

**Xong khi:** cả nhóm chạy được mock; Supabase có đủ bảng.

### Tuần 2–3 – T7: nối thật
- [ ] Đặt `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` trong `.env`: log tự ghi vào bảng `chat_logs` thay vì file.
- [ ] Thêm test: câu hỏi 1001 ký tự trả 422; hỏi 2 lần liên tiếp trả 429.
- [ ] Cùng Khiêm chạy với `LLM_PROVIDER=anthropic`: kiểm tra stream vẫn chạy dần, lỗi API key sai thì UI nhận sự kiện `error`.
- [ ] Deploy thử backend lên Render hoặc Railway (gói miễn phí): khai báo biến môi trường trên trang quản trị, **không** upload `.env`.

**Xong khi:** hỏi trên bản deploy thử nhận câu trả lời thật, log có trong Supabase.

### Tuần 4 – T12
- [ ] `/api/feedback` ghi vào bảng `feedback`.
- [ ] Endpoint nhỏ cho nhóm xem nhanh: `GET /admin/stats` (có `X-Admin-Token`) trả số câu hỏi, tỉ lệ đúng/sai theo feedback.

### Tuần 5 – T19: kiểm soát chi phí API
Phương án A gọi API trả tiền theo token, prompt RAG lại dài, nên phải làm trước khi mở cho người ngoài.
- [ ] Ghi số token vào/ra của mỗi câu (lấy từ phản hồi API) vào `chat_logs`, cộng thành chi phí ước tính theo ngày.
- [ ] Đặt hạn mức trong `.env`, vd. `DAILY_QUESTION_LIMIT=500`. Vượt hạn mức thì trả `RATE_LIMITED` kèm thông báo dễ hiểu.
- [ ] Cache: câu hỏi giống hệt câu đã hỏi trong 24 giờ thì trả lại câu trả lời cũ.
- [ ] Bật cảnh báo ngân sách trên trang quản trị của nhà cung cấp API.

**Xong khi:** biết hôm qua tốn bao nhiêu tiền, và không thể vượt hạn mức đã đặt.

### Tuần 7 – T16: deploy công khai
- [ ] `CORS_ORIGINS` chỉ còn domain của UI.
- [ ] Giới hạn tần suất theo cả IP (tránh một người spam tốn tiền API).
- [ ] Kiểm tra `/api/health` trả đúng provider và model đang dùng.

## 7. Lỗi thường gặp

| Hiện tượng | Nguyên nhân hay gặp |
| --- | --- |
| `ModuleNotFoundError: app` | Chạy uvicorn ngoài thư mục `backend/` |
| Đổi `.env` mà không thấy tác dụng | Phải tắt và chạy lại uvicorn (`--reload` chỉ theo dõi file `.py`) |
| Supabase báo `permission denied` | Đang dùng `anon key`; backend phải dùng `service_role key` |
| Lên host thì không stream, chờ rồi ra cả cục | Host bật nén/gom response; tìm cách tắt buffering cho đường dẫn `/api/chat` |

## 8. Bàn giao

- Giao UI và Eval: hợp đồng API (đã có), địa chỉ backend deploy.
- Nhận từ AI: `pipeline.answer()` đã chạy thật (tuần 3).
