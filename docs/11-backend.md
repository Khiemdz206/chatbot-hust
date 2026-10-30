# Phần Backend – TV4

**Thư mục được sửa:** `backend/app/` **trừ** `backend/app/rag/` (của Khiêm), `backend/tests/`, file mới trong `supabase/migrations/`, `.env.example` · **Task:** T3, T7b, T12b, T19, T16a · Phần UI của bạn: [10-ui.md](10-ui.md)

Việc của bạn: lớp mỏng giữa UI và AI. Nhận câu hỏi, kiểm tra, gọi `pipeline.answer()`, đẩy kết quả về UI theo từng chữ, ghi log, giới hạn tần suất và tải cho máy Mac chạy model. **Không viết logic AI ở đây** (tìm kiếm, prompt, gọi model) để Khiêm đổi bên trong `rag/` mà không ảnh hưởng API.

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

### T7b – Nối thật và chạy chung trên máy Mac (tuần 3)

**Mục tiêu:** backend chạy trên máy Mac cùng Ollama, trả lời thật, log vào Supabase, lỗi model được báo đúng cho UI. Cả nhóm trong cùng Wi-Fi dùng được.

Nhóm không dùng API trả tiền: model chạy bằng Ollama trên máy Mac, nên **backend cũng chạy trên máy Mac đó** (không deploy lên host miễn phí: host không có model, và bge-m3 cần ~3 GB RAM).

**Các bước:**

1. **Test mới** trong `backend/tests/test_api.py`:
   - `message` 1001 ký tự → 422.
   - Hai câu liên tiếp cùng `session_id` khi `MIN_SECONDS_BETWEEN_QUESTIONS > 0` → câu thứ hai 429, body `{"code": "RATE_LIMITED", ...}`. (File test đặt biến này bằng `0`; đổi tạm `settings.min_seconds_between_questions` trong test bằng `monkeypatch.setattr`.)
   - `pipeline.answer` ném exception → stream có `event: error`, không stream trả 502. Dùng `monkeypatch.setattr(pipeline, "answer", hàm_lỗi)`.
2. Cùng Khiêm chạy trên Mac với `LLM_PROVIDER=ollama`: stream vẫn chạy dần; tắt Ollama giữa chừng → UI nhận sự kiện `error` với thông báo tiếng Việt.
3. Lỗi `log_feedback` hiện làm `/api/feedback` trả 500: bọc `try/except` giống `log_chat`, vẫn trả `{"ok": true}` và `print` lỗi.
4. Trên Mac chạy `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Từ máy khác cùng Wi-Fi mở `http://<ip-cua-mac>:8000` (IP: *System Settings → Wi-Fi → Details*). Wi-Fi trường chặn thì dùng hotspot điện thoại.
5. Viết script `backend/run_mac.sh` khởi động một lệnh: kiểm tra Ollama đang chạy (`curl -s localhost:11434`), rồi chạy uvicorn như trên.

**Kiểm tra:** `pytest -q` pass hết (≥ 9 test); máy khác hỏi qua `http://<ip-cua-mac>:8000` nhận câu trả lời thật; `chat_logs` có dòng tương ứng.

**Bàn giao:** gửi địa chỉ cho TV3 và Khiêm.

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

### T19 – Giới hạn tải cho máy Mac (tuần 5)

**Mục tiêu:** nhiều người hỏi cùng lúc thì máy Mac không bị treo, người hỏi nhận thông báo rõ ràng thay vì chờ mãi.

Model local trả lời từng câu một (Ollama mặc định xử lý ít câu song song). Mỗi câu mất 5–20 giây; 10 người hỏi cùng lúc thì người cuối chờ vài phút. Không tốn tiền, nhưng phải giới hạn tải.

**Các bước:**

1. Thêm vào `config.py` + `.env.example`: `MAX_CONCURRENT_ANSWERS` (mặc định `2`), `MAX_WAITING` (mặc định `5`), `DAILY_QUESTION_LIMIT` (mặc định `1000`).
2. Trong `main.py`: dùng `asyncio.Semaphore(MAX_CONCURRENT_ANSWERS)` bao quanh việc gọi `pipeline.answer`. Đếm số request đang chờ; quá `MAX_WAITING` thì trả ngay 429 `RATE_LIMITED`, `message`: "Chatbot đang bận trả lời nhiều người, bạn thử lại sau ít phút nhé."
3. Trong lúc chờ đến lượt, UI vẫn hiện "Đang tìm văn bản liên quan…" nên không cần đổi hợp đồng. Muốn hiện "Đang xếp hàng (2 người trước bạn)" thì thêm sự kiện `queue` vào [02-api-contract.md](02-api-contract.md) và sửa `web/app.js` trong cùng PR.
4. Hạn mức ngày: đếm số câu trong ngày (giờ Việt Nam, UTC+7) trong RAM, vượt thì 429 với thông báo "quay lại vào ngày mai".
5. Cache: câu hỏi giống hệt (so sau `strip().lower()` và chuẩn hoá NFC), **không có `history`**, trong 24 giờ → trả lại câu trả lời cũ (vẫn phát SSE như bình thường, `answer_id` mới). Lưu trong RAM, tối đa 1.000 mục. Giảm tải cho Mac rất nhiều với các câu hay hỏi.
6. Thêm vào `/admin/stats`: `waiting_now`, `cache_hits_today`.
7. Trên Mac, đặt `OLLAMA_NUM_PARALLEL` bằng `MAX_CONCURRENT_ANSWERS` (`launchctl setenv OLLAMA_NUM_PARALLEL 2`, rồi mở lại Ollama). Đo: 2 câu song song có chậm hơn 1 câu nhiều không; chậm quá thì đặt `1`.

**Kiểm tra:** test hàng chờ (monkeypatch `pipeline.answer` thành hàm chờ 1 giây, gửi `MAX_WAITING + MAX_CONCURRENT_ANSWERS + 1` request song song → có request nhận 429); test hạn mức ngày (`DAILY_QUESTION_LIMIT=2`, câu thứ 3 → 429); test cache (hỏi 2 lần cùng câu, `pipeline.answer` chỉ bị gọi 1 lần).

### T16a – Mở công khai (tuần 7)

Backend và Ollama chạy trên máy Mac. Mở **backend** (không phải Ollama) ra Internet bằng Cloudflare Tunnel.

**Các bước:**

1. Trên Mac: cài `cloudflared` (`brew install cloudflared`). Thử nhanh: `cloudflared tunnel --url http://localhost:8000` → in ra một địa chỉ `https://<ngau-nhien>.trycloudflare.com`. Địa chỉ này đổi mỗi lần chạy; cần địa chỉ cố định thì tạo tunnel có tên (cần tài khoản Cloudflare miễn phí và một tên miền).
2. Mở địa chỉ đó trên điện thoại qua 4G: hỏi được, chữ chạy dần (nếu ra cả cục thì kiểm tra buffering).
3. Lấy IP thật của người hỏi từ header `CF-Connecting-IP` (hoặc `X-Forwarded-For`) để giới hạn tần suất theo **cả IP**, không chỉ `session_id`. Dọn `_last_seen` định kỳ để không phình RAM.
4. `CORS_ORIGINS`: nếu UI do backend phục vụ (mặc định) thì đặt đúng domain tunnel; không để `*`.
5. Đặt `ADMIN_TOKEN` dài, ngẫu nhiên.
6. Máy Mac phải cắm sạc, không ngủ (`caffeinate -i`), không chạy việc nặng khác trong giờ mở công khai. Ghi giờ mở vào trang Giới thiệu.
7. `/api/health` trả đúng `ollama` và model đang dùng.

**Bàn giao:** gửi link công khai cho cả nhóm (TV3 cần cho T16b).

### T17 – Báo cáo phần UI + Backend (tuần 8)

Kiến trúc, các trạng thái UI, cách stream, giới hạn tần suất và tải, cách mở công khai từ máy Mac, số liệu từ `/admin/stats`.

## 4. Lỗi thường gặp

| Hiện tượng | Nguyên nhân hay gặp |
| --- | --- |
| `ModuleNotFoundError: app` | Chạy uvicorn/pytest ngoài thư mục `backend/` |
| Đổi `.env` mà không thấy tác dụng | Phải tắt và chạy lại uvicorn |
| Test hỏng vì đọc `.env` thật của bạn | Test phải đặt `os.environ[...]` trước `from app.main import app`; `load_dotenv` không ghi đè biến đã có |
| Supabase báo `permission denied` | Đang dùng `anon key`; backend phải dùng `service_role key` |
| Qua tunnel thì không stream, chờ rồi ra cả cục | Proxy gom response; backend đã đặt `X-Accel-Buffering: no`, kiểm tra cấu hình tunnel |
| Máy khác không vào được `http://<ip-cua-mac>:8000` | Chưa chạy uvicorn với `--host 0.0.0.0`; tường lửa macOS; Wi-Fi trường chặn (dùng hotspot) |
| Câu đầu rất chậm hoặc Mac hết RAM | Đang nạp bge-m3 và model Ollama; cộng RAM theo [14-finetune.md, tuần 1](14-finetune.md#tuần-1--chọn-model-và-máy-chạy) |
| UI báo lỗi `UPSTREAM_ERROR` liên tục | Ollama chưa chạy hoặc sai `LLM_MODEL`; thử `ollama list` |
