# Phần Backend – TV4

**Thư mục được sửa:** `backend/app/` **trừ** `backend/app/rag/` (của Khiêm), `backend/tests/`, file mới trong `supabase/migrations/`, `.env.example` · **Task:** T3, T7b, T12b, T19, T16a · Phần UI của bạn: [10-ui.md](10-ui.md)

Việc của bạn: lớp mỏng giữa UI và AI. Nhận câu hỏi, kiểm tra, gọi `pipeline.answer()`, đẩy kết quả về UI theo từng chữ, ghi log, giới hạn tần suất và chi phí. **Không viết logic AI ở đây** (tìm kiếm, prompt, gọi model) để Khiêm đổi bên trong `rag/` mà không ảnh hưởng API.

## 1. Code hiện có

| File | Nội dung |
| --- | --- |
| `backend/app/config.py` | Đọc `.env` ở thư mục gốc vào `settings`. Nơi **duy nhất** đọc biến môi trường. Dùng chung với `rag/` |
| `backend/app/schemas.py` | Pydantic: `ChatRequest`, `Turn`, `Source`, `ChatResponse`, `FeedbackRequest`. Phải khớp [02-api-contract.md](02-api-contract.md) |
| `backend/app/main.py` | App FastAPI: CORS, `_check_rate()` (giới hạn theo `session_id`, rơi về IP nếu không có, lưu trong dict `_last_seen` trong RAM), `_sse()`, endpoint `/api/health`, `/api/chat`, `/api/feedback`, `/admin/reindex` (chưa cài), handler lỗi `HTTPException` → `{"code","message"}`, mount `web/` ở `/` |
| `backend/app/store.py` | `store.log_chat(row)`, `store.log_feedback(row)`: có `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` thì insert vào bảng `chat_logs`/`feedback`, không thì ghi `backend/logs/<bảng>.jsonl`. `log_chat` nuốt lỗi; `log_feedback` thì không |
| `backend/tests/test_api.py` | 6 test ở chế độ mock |
| `supabase/migrations/001_init.sql` | Bảng `documents`, `chunks`, `chat_logs`, `feedback`, hàm `match_chunks` |

Luồng `/api/chat` trong `main.py`:

1. Pydantic kiểm `message` (1–1000 ký tự) → sai thì 422.
2. `_check_rate(session_id hoặc IP)` → quá nhanh thì 429 `RATE_LIMITED`.
3. `run()` gọi `pipeline.answer(message, history)`, gom `token`/`sources`/`meta` vào `state`.
4. `stream=false`: chạy hết, trả `ChatResponse`. Mặc định: phát SSE `token`… → `sources` → `done`.
5. `log_row(state)` dựng dòng `chat_logs`; ghi nền bằng `asyncio.create_task(store.log_chat(row))`.
6. Exception giữa chừng: stream thì gửi sự kiện `error`, không stream thì 502.

## 2. Chạy và thử

```bash
cd backend
source .venv/bin/activate          # Windows: .venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
pytest -q                          # terminal khác; phải ra 6 passed
```

- <http://localhost:8000/docs>: trang thử API. Bấm `POST /api/chat` → *Try it out*.
- Thử stream:
  ```bash
  curl -N -X POST "http://localhost:8000/api/chat" -H "Content-Type: application/json" \
    -d '{"message":"Học phí tính theo tín chỉ ra sao?"}'
  ```
- `--reload` chỉ theo dõi file `.py`. Đổi `.env` thì tắt và chạy lại.

Mỗi thay đổi hành vi API phải có test trong `backend/tests/`. Test đặt biến môi trường ở đầu file **trước** khi import `app.main` (vì `settings` đọc lúc import).

## 3. Task

### T3 – Làm quen và tạo Supabase (tuần 1)

**Mục tiêu:** cả nhóm chạy được mock; Supabase có đủ bảng; mọi người có thông tin kết nối.

**Các bước:**

1. Chạy mock và `pytest` theo mục 2. Đọc `main.py` từ hàm `chat()`.
2. Tạo project trên supabase.com (gói miễn phí, region Singapore). Mời Khiêm và TV2 vào (Organization → Members).
3. Supabase → **SQL Editor** → dán toàn bộ `supabase/migrations/001_init.sql` → Run.
4. **Table Editor**: kiểm tra có 4 bảng `documents`, `chunks`, `chat_logs`, `feedback`. **Database → Functions**: có `match_chunks`.
5. **Project Settings → API**: lấy `Project URL` và `service_role` key. Gửi cho Khiêm, TV2, TV3 **qua tin nhắn riêng**. Không đưa lên Git, không dán vào nhóm chat chung.

**Kiểm tra:** đặt `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` trong `.env` của bạn (giữ `RETRIEVER=mock`), khởi động lại backend, hỏi một câu → bảng `chat_logs` có một dòng mới.

**Bàn giao:** báo TV2 "Supabase sẵn sàng" (TV2 cần cho T4).

### T7b – Nối thật và deploy thử (tuần 3)

**Mục tiêu:** bản deploy thử trả lời thật, log vào Supabase, lỗi model được báo đúng cho UI.

**Các bước:**

1. **Test mới** trong `backend/tests/test_api.py`:
   - `message` 1001 ký tự → 422.
   - Hai câu liên tiếp cùng `session_id` khi `MIN_SECONDS_BETWEEN_QUESTIONS > 0` → câu thứ hai 429, body `{"code": "RATE_LIMITED", ...}`. (File test đặt biến này bằng `0`; đổi tạm `settings.min_seconds_between_questions` trong test bằng `monkeypatch.setattr`.)
   - `pipeline.answer` ném exception → stream có `event: error`, không stream trả 502. Dùng `monkeypatch.setattr(pipeline, "answer", hàm_lỗi)`.
2. Cùng Khiêm chạy với `LLM_PROVIDER=anthropic`: stream vẫn chạy dần; đặt sai `ANTHROPIC_API_KEY` → UI nhận sự kiện `error` với thông báo tiếng Việt.
3. Lỗi `log_feedback` hiện làm `/api/feedback` trả 500: bọc `try/except` giống `log_chat`, vẫn trả `{"ok": true}` và `print` lỗi.
4. **Deploy thử** (Render hoặc Railway): Start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, Root directory `backend`. Khai báo biến môi trường trên trang quản trị của host, **không** upload `.env`. Lưu ý RAM: xem T16a.
5. Kiểm tra `/api/health` trên bản deploy.

**Kiểm tra:** `pytest -q` pass hết (≥ 9 test); hỏi trên bản deploy nhận câu trả lời thật; `chat_logs` có dòng tương ứng.

**Bàn giao:** gửi URL bản deploy cho TV3 và Khiêm.

### T12b – Thống kê cho nhóm (tuần 4)

**Mục tiêu:** `GET /admin/stats` cho nhóm xem nhanh tình hình mà không cần mở Supabase.

**Các bước:**

1. Kiểm tra `/api/feedback` đã ghi vào bảng `feedback` khi có Supabase (code đã có trong `store.py`, chỉ cần thử).
2. Thêm `GET /admin/stats`, header `X-Admin-Token` (kiểm như `/admin/reindex`). Trả:
   ```json
   {"questions_today": 42, "questions_7d": 310, "refused_rate_7d": 0.12,
    "feedback_7d": {"up": 20, "down": 5}, "avg_latency_ms_7d": 2300}
   ```
   Bỏ các dòng `session_id = 'eval'`. Thêm hàm đọc vào `store.py` (với chế độ file: đọc `backend/logs/*.jsonl`).
3. Ghi endpoint vào [02-api-contract.md mục 3](02-api-contract.md#3-endpoint-khác).

**Kiểm tra:** test cho 401 khi sai token và 200 với đúng các khoá trên.

### T19 – Kiểm soát chi phí API (tuần 5)

**Mục tiêu:** biết mỗi ngày tốn bao nhiêu tiền và không thể vượt hạn mức. Phương án A trả tiền theo token, prompt RAG dài (~3.000–5.000 token mỗi câu), nên phải xong trước khi mở cho người ngoài.

**Cần trước:** Khiêm thêm `usage: {"input_tokens", "output_tokens"}` vào sự kiện `meta` của `pipeline.answer` ([02-api-contract.md mục 5](02-api-contract.md#5-pipelineanswer-hợp-đồng-giữa-backend-và-ai)). Nhắn Khiêm đầu tuần 5. Trong lúc chờ, coi `usage` là `None`.

**Các bước:**

1. Migration mới `supabase/migrations/002_usage.sql`:
   ```sql
   alter table chat_logs add column if not exists input_tokens int, add column if not exists output_tokens int;
   ```
   Chạy trong SQL Editor. Ghi hai cột này trong `log_row()` từ `meta.get("usage")`.
2. Thêm vào `config.py` + `.env.example`: `DAILY_QUESTION_LIMIT` (mặc định `500`), `PRICE_INPUT_PER_MTOK`, `PRICE_OUTPUT_PER_MTOK` (giá USD trên 1 triệu token của model đang dùng, lấy ở trang giá của nhà cung cấp).
3. Hạn mức ngày: đếm số câu hỏi trong ngày (theo giờ Việt Nam, UTC+7) trong RAM, reset khi sang ngày mới. Vượt thì 429 `RATE_LIMITED`, `message`: "Hôm nay chatbot đã nhận quá nhiều câu hỏi, bạn quay lại vào ngày mai nhé." Câu từ chối do không tìm thấy văn bản (không gọi model) không tính.
4. Cache: câu hỏi giống hệt (so sau khi `strip().lower()` và chuẩn hoá NFC), **không có `history`**, trong 24 giờ → trả lại câu trả lời cũ (vẫn phát SSE như bình thường, `answer_id` mới). Lưu cache trong RAM, tối đa 1.000 mục.
5. Thêm vào `/admin/stats`: `cost_usd_today`, `cost_usd_7d` = tổng token × giá.
6. Nhắc Khiêm bật cảnh báo ngân sách trên trang quản trị của nhà cung cấp API.

**Kiểm tra:** test hạn mức (đặt `DAILY_QUESTION_LIMIT=2`, câu thứ 3 → 429); test cache (hỏi 2 lần cùng câu, `pipeline.answer` chỉ bị gọi 1 lần — đếm bằng monkeypatch).

### T16a – Deploy công khai (tuần 7)

**Các bước:**

1. **Chọn nơi chạy** (bàn với Khiêm trong tuần 5–6). `RETRIEVER=supabase` tải model embedding `BAAI/bge-m3` vào RAM (~2,5–3 GB) ngay trong backend. Gói miễn phí của Render/Railway (512 MB–1 GB) **không chạy nổi**. Các lựa chọn:
   - Chạy backend trên máy của nhóm (máy Mac dùng cho phương án B) + Cloudflare Tunnel/ngrok mở ra ngoài. Rẻ nhất, máy phải bật suốt.
   - Thuê host ≥ 4 GB RAM.
   - Khiêm đổi sang embedding qua API (phải embed lại toàn bộ và đổi số chiều vector; việc lớn, chỉ làm nếu hai cách trên không được).
2. `CORS_ORIGINS` chỉ còn domain của UI (nếu UI tách riêng), không để `*`.
3. Giới hạn tần suất theo **cả IP**, không chỉ `session_id` (người dùng đổi `session_id` dễ dàng). Lấy IP thật từ header `X-Forwarded-For` khi chạy sau proxy/tunnel. Dọn `_last_seen` định kỳ để không phình RAM.
4. Đặt `ADMIN_TOKEN` dài, ngẫu nhiên.
5. `/api/health` trả đúng provider và model đang dùng; UI hỏi được từ điện thoại qua 4G.

**Bàn giao:** gửi link công khai cho cả nhóm (TV3 cần cho T16b).

### T17 – Báo cáo phần UI + Backend (tuần 8)

Kiến trúc, các trạng thái UI, cách stream, giới hạn tần suất/chi phí, nơi deploy, số liệu từ `/admin/stats`.

## 4. Lỗi thường gặp

| Hiện tượng | Nguyên nhân hay gặp |
| --- | --- |
| `ModuleNotFoundError: app` | Chạy uvicorn/pytest ngoài thư mục `backend/` |
| Đổi `.env` mà không thấy tác dụng | Phải tắt và chạy lại uvicorn |
| Test hỏng vì đọc `.env` thật của bạn | Test phải đặt `os.environ[...]` trước `from app.main import app`; `load_dotenv` không ghi đè biến đã có |
| Supabase báo `permission denied` | Đang dùng `anon key`; backend phải dùng `service_role key` |
| Lên host thì không stream, chờ rồi ra cả cục | Host bật nén/gom response; tắt buffering cho `/api/chat` |
| Host báo hết bộ nhớ khi hỏi câu đầu | Đang tải bge-m3 (xem T16a) |
