# Hợp đồng giữa các phần

File này ghi **mọi định dạng dữ liệu đi từ phần này sang phần khác**: API HTTP, sự kiện của pipeline, file JSONL, bảng CSDL, biến `.env`. Ai cũng code theo file này nên 4 người làm song song được.

**Muốn đổi bất cứ thứ gì ở đây:** báo người dùng định dạng đó (cột "Ai đọc"), sửa file này trong cùng PR với code.

| Mục | Ai tạo | Ai đọc | Code tương ứng |
| --- | --- | --- | --- |
| [1. `POST /api/chat`](#1-post-apichat) | TV4 (BE) | TV4 (UI), TV3 (eval) | `backend/app/main.py`, `backend/app/schemas.py`, `web/app.js`, `eval/run_eval.py` |
| [2. `POST /api/feedback`](#2-post-apifeedback) | TV4 | TV4 | `main.py`, `store.py` |
| [3. Endpoint khác](#3-endpoint-khác) | TV4 | cả nhóm | `main.py` |
| [4. Mã lỗi](#4-mã-lỗi) | TV4 | TV4, TV3 | `main.py`, `web/app.js` |
| [5. `pipeline.answer()`](#5-pipelineanswer-hợp-đồng-giữa-backend-và-ai) | Khiêm | TV4 | `backend/app/rag/pipeline.py` |
| [6. `chunks.jsonl`](#6-datachunkschunksjsonl) | TV2 | Khiêm (fine-tune) | `data/chunk.py`, `finetune/make_sft_dataset.py` |
| [7. Bảng Supabase](#7-bảng-supabase) | TV2 + TV4 | Khiêm, TV4 | `supabase/migrations/`, `data/embed_upload.py`, `rag/retriever.py`, `store.py` |
| [8. Bộ đề `golden/*.jsonl`](#8-bộ-đề-evalgoldenjsonl) | TV3 | Khiêm (recall@k, lọc dataset) | `eval/run_eval.py`, `finetune/make_sft_dataset.py` |
| [9. Kết quả eval](#9-kết-quả-eval-evalresults) | TV3 | cả nhóm | `eval/run_eval.py`, `eval/judge.py`, `eval/RUBRIC.md` |
| [10. Dataset SFT](#10-dataset-sft-finetunedatasetssftjsonl) | Khiêm (agent cả nhóm viết) | Khiêm (Colab) | `finetune/make_sft_dataset.py`, `finetune/TEACHER.md`, `finetune/train_lora_colab.py` |
| [11. Mã chủ đề](#11-mã-chủ-đề-topic) | – | cả nhóm | `data/sources.yaml`, `eval/golden/` |
| [12. Biến `.env`](#12-biến-env) | – | cả nhóm | `.env.example`, `backend/app/config.py` |

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
| `session_id` | không | ≤ 100 ký tự; dùng để giới hạn tần suất và gom log. UI tạo bằng `crypto.randomUUID()` và lưu `localStorage["chatbot-session"]`. Eval gửi `"eval"`. |
| `history` | không | tối đa 12 phần tử, mỗi `content` ≤ 4000 ký tự; UI gửi 6 phần tử gần nhất |

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
- `sources`: đúng một lần. `n` khớp với số `[n]` trong câu trả lời. Có thể là mảng rỗng. `section`, `url`, `effective_date` có thể `null`.
- `done`: đúng một lần, cuối cùng. `answer_id` dùng cho feedback. `refused: true` nghĩa là chatbot từ chối (không tìm thấy văn bản hoặc ngoài phạm vi).
- `error`: thay cho `done` khi lỗi giữa chừng: `{"code": "UPSTREAM_ERROR", "message": "..."}`. Sau `error` không có sự kiện nào nữa.

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
{"answer_id": "uuid", "rating": 1, "comment": "tuỳ chọn, ≤ 1000 ký tự"}
```

`rating`: `1` (đúng) hoặc `-1` (sai). Trả `{"ok": true}`. Ghi vào bảng `feedback`.

## 3. Endpoint khác

| Endpoint | Trả về | Ghi chú |
| --- | --- | --- |
| `GET /api/health` | `{"status": "ok", "llm_provider": "ollama", "llm_model": "chatbot-hust", "retriever": "supabase"}` | Kiểm tra backend đang chạy cấu hình nào |
| `POST /admin/reindex` | `{"ok": true, "message": "..."}` | Header `X-Admin-Token: <ADMIN_TOKEN>`. Chưa cài (T9) |
| `GET /admin/stats` | xem [11-backend.md, T12b](11-backend.md#t12b--thống-kê-cho-nhóm-tuần-4) | Header `X-Admin-Token`. Chưa cài (T12b) |
| `GET /docs` | Trang thử API do FastAPI tự sinh | |
| `GET /` | Giao diện trong `web/` | Backend phục vụ thư mục `web/` |

## 4. Mã lỗi

Mọi lỗi HTTP do backend tự trả có body `{"code": "...", "message": "..."}`.

| HTTP | `code` | Khi nào | UI hiển thị |
| --- | --- | --- | --- |
| 401 | `UNAUTHORIZED` | Sai `X-Admin-Token` | – |
| 422 | (body mặc định của FastAPI, có trường `detail`) | `message` rỗng hoặc quá dài | "Câu hỏi không hợp lệ" |
| 429 | `RATE_LIMITED` | Cùng `session_id` hỏi lại trong < `MIN_SECONDS_BETWEEN_QUESTIONS` giây; (sau T19) hàng chờ đầy hoặc vượt hạn mức ngày | Hiện `message` từ backend |
| 502 / sự kiện `error` | `UPSTREAM_ERROR` | Model hoặc CSDL lỗi | Thông báo + nút "Thử lại" |

## 5. `pipeline.answer()`: hợp đồng giữa Backend và AI

Backend chỉ gọi đúng một hàm:

```python
from app.rag import pipeline

async for ev in pipeline.answer(question: str, history: list[dict]):
    ...
```

Các sự kiện, đúng thứ tự:

| `ev["type"]` | Số lần | Các trường khác |
| --- | --- | --- |
| `"token"` | ≥ 1 | `text: str` |
| `"sources"` | 1 | `items: list[dict]`, mỗi phần tử `{n, title, section, url, effective_date}` (giống mục 1) |
| `"meta"` | 1, cuối cùng | `refused: bool`, `rewritten: str`, `model: str`, `chunk_ids: list[str]` (rỗng khi refused), `cited: list[int]` (khi không refused) |

- Khiêm được sửa mọi thứ bên trong `backend/app/rag/` miễn giữ đúng bảng trên.
- Thêm trường vào `meta` thì được (backend bỏ qua trường lạ). Bỏ hoặc đổi tên trường thì phải báo TV4.
- `pipeline.answer` có thể ném exception; backend bắt và trả `UPSTREAM_ERROR`.

Kiểu `Chunk` (`backend/app/rag/retriever.py`), dùng chung với fine-tune:

```python
@dataclass
class Chunk:
    id: str
    title: str
    content: str
    section: str | None = None
    url: str | None = None
    effective_date: str | None = None
    score: float = 0.0
```

## 6. `data/chunks/chunks.jsonl`

Do `data/chunk.py` tạo, mỗi dòng một chunk:

```json
{"source_id": "quy-che-dao-tao-2025", "title": "Quy chế đào tạo đại học", "url": "https://...",
 "doc_type": "quy_che", "topic": "diem", "effective_date": "2025-08-01", "applies_to": "K70 trở đi",
 "content_hash": "sha256...", "chunk_index": 12, "section": "Chương II – Điều 12. Đăng ký học tập",
 "content": "1. Sinh viên ..."}
```

- `source_id` = `id` trong `sources.yaml`. `source_id` + `chunk_index` là duy nhất. Fine-tune dùng `"<source_id>#<chunk_index>"` làm id chunk.
- `url` phải **khác nhau giữa các văn bản**: `embed_upload.py` gom chunk theo `url`.
- `section` dạng `"Chương <số La Mã>. <tên> – Điều <số>. <tên>"`, hoặc `null` với văn bản không chia Điều.

## 7. Bảng Supabase

Định nghĩa đầy đủ: `supabase/migrations/001_init.sql`. Không sửa file migration đã chạy; muốn đổi thì thêm file mới `002_<mo-ta>.sql`, `003_...`.

| Bảng | Ai ghi | Cột chính |
| --- | --- | --- |
| `documents` | `data/embed_upload.py` | `id`, `title`, `url` (unique), `doc_type`, `topic`, `effective_date`, `applies_to`, `is_active`, `content_hash` |
| `chunks` | `data/embed_upload.py` | `id`, `document_id`, `chunk_index`, `section`, `content`, `embedding vector(1024)`, `tsv` (tự sinh) |
| `chat_logs` | `backend/app/store.py` | `id` (= `answer_id`), `session_id`, `question`, `rewritten_question`, `answer`, `chunk_ids text[]`, `model`, `refused`, `latency_ms`, `created_at` |
| `feedback` | `backend/app/store.py` | `answer_id`, `rating` (1/-1), `comment`, `created_at` |

Hàm tìm kiếm (backend gọi qua `client.rpc`):

```sql
match_chunks(query_embedding vector(1024), query_text text, match_count int default 6, rrf_k int default 50)
returns table (id bigint, document_id bigint, section text, content text, title text, url text, effective_date date, score float)
```

- Chỉ trả chunk của văn bản `is_active = true`.
- `vector(1024)` là số chiều của `BAAI/bge-m3`. Đổi model embedding thì phải đổi số chiều **và** embed lại toàn bộ.
- `chat_logs.chunk_ids` là `id` của bảng `chunks` (dạng chuỗi).

## 8. Bộ đề `eval/golden/*.jsonl`

Mỗi dòng một câu:

```json
{"id": "DKHP-007", "topic": "dkhp", "difficulty": "medium", "in_scope": true,
 "question": "đkhp bổ sung muộn có bị phạt k ạ",
 "reference_answer": "Đáp án đúng, ngắn, lấy từ văn bản chính thức",
 "reference_source": "https://ctt.hust.edu.vn/...#Điều 12",
 "hustva_answer": "Chép nguyên văn câu trả lời của HustVA",
 "collected_at": "2026-11-05", "collected_by": "TV3"}
```

| Trường | Bắt buộc | Quy ước |
| --- | --- | --- |
| `id` | có | `<TIỀN TỐ CHỦ ĐỀ>-<3 chữ số>`, vd. `DKHP-007`, `HP-012`, `NPV-003`. Không đổi id đã có. |
| `topic` | có | Một mã ở [mục 11](#11-mã-chủ-đề-topic) |
| `difficulty` | có | `easy` (một ý trong một Điều) · `medium` (ghép 2 ý) · `hard` (nhiều văn bản, điều kiện, ngoại lệ) |
| `in_scope` | có | `false` cho câu ngoài phạm vi (topic `ngoai_pham_vi`) |
| `question` | có | Viết như sinh viên nhắn tin thật |
| `reference_answer` | có | Câu ngoài phạm vi: ghi `"Từ chối, gợi ý chủ đề hỗ trợ"` |
| `reference_source` | có nếu `in_scope` | **Đúng dạng `<url>#Điều <số>`**, nhiều nguồn ngăn bằng ` ; `. `<url>` phải trùng `url` trong `sources.yaml`. Văn bản không có Điều: chỉ ghi `<url>`. Script recall@k của Khiêm đọc trường này. |
| `hustva_answer` | có | Chép nguyên văn. HustVA không trả lời: ghi `""` |
| `collected_at`, `collected_by` | có | Ngày hỏi HustVA (`YYYY-MM-DD`), người hỏi |

Các dòng có `id` bắt đầu bằng `MAU-` là mẫu, xoá khi có câu thật.

## 9. Kết quả eval (`eval/results/`)

- `run_eval.py` → `results/<YYYYMMDD-HHMM>_<commit>.jsonl`: mỗi dòng = dòng bộ đề + `system_answer`, `system_sources`, `system_refused`, `error`, `latency_ms`.
- `judge.py prepare` → `<cùng tên>.judge_tasks.jsonl` (mỗi dòng `{id, question, in_scope, reference_answer, reference_source, A, B}`, A/B đảo ngẫu nhiên) và `<cùng tên>.judge_key.json` (`{id: {"ours": "A"|"B", "hustva": "A"|"B"}}`).
- Agent chấm theo `eval/RUBRIC.md` → `<cùng tên>.judge_scores.jsonl`: mỗi dòng `{"id", "A": {...}, "B": {...}, "unsure": bool}`, mỗi `{...}` là `{"correct": 0|1|2, "hallucination": bool, "cites_source": bool, "note": str}`.
- `judge.py report` → `<cùng tên>.judged.jsonl` (thêm `scores: {"ours": {...}, "hustva": {...}}` hoặc `null` nếu chưa chấm, và `can_cham_tay`) và `<cùng tên>.report.md`.
- `eval/results/` không lên Git. Báo cáo dùng để so sánh thì chép vào `eval/reports/` và commit.

## 10. Dataset SFT (`finetune/datasets/sft.jsonl`)

```json
{"messages": [{"role": "system", "content": "<SYSTEM_PROMPT>"},
              {"role": "user", "content": "<tai_lieu>...</tai_lieu>\n\nCâu hỏi: ..."},
              {"role": "assistant", "content": "..."}],
 "meta": {"target": "quy-che-dao-tao-2025#12", "answerable": true}}
```

Phần `user` được tạo bằng đúng `build_messages()` trong `backend/app/rag/prompts.py`. Đổi `SYSTEM_PROMPT` hoặc `format_context()` thì dataset cũ hết dùng được.

File trung gian (agent đọc/ghi, chi tiết trong `finetune/TEACHER.md`):

| File | Ai ghi | Mỗi dòng |
| --- | --- | --- |
| `datasets/q_tasks/batch_XXX.jsonl` | script (`questions`) | `{chunk_id, title, section, content}` |
| `datasets/q_tasks/batch_XXX.out.jsonl` | agent | `{chunk_id, questions: [str]}` |
| `datasets/a_tasks/batch_XXX.jsonl` | script (`contexts`) | `{task_id, answerable, user}` |
| `datasets/a_tasks/batch_XXX.out.jsonl` | agent | `{task_id, answer}` |

## 11. Mã chủ đề (`topic`)

Dùng chung cho `sources.yaml` và bộ đề:

| Mã | Chủ đề | Tiền tố id bộ đề |
| --- | --- | --- |
| `quy_che` | Quy chế đào tạo chung (tín chỉ, cảnh báo học tập, chuyển ngành...) | `QC` |
| `dkhp` | Đăng ký học phần | `DKHP` |
| `hoc_phi` | Học phí | `HP` |
| `diem` | Điểm, cách tính CPA/GPA, học lại, cải thiện | `DIEM` |
| `tot_nghiep` | Điều kiện tốt nghiệp | `TN` |
| `hoc_bong` | Học bổng | `HB` |
| `thong_bao` | Thông báo trên CTT | `TB` |
| `khac` | Thứ khác trong phạm vi | `KHAC` |
| `ngoai_pham_vi` | Câu ngoài phạm vi (chỉ có trong bộ đề) | `NPV` |

## 12. Biến `.env`

File `.env` ở thư mục gốc, mẫu là `.env.example`. Thêm biến mới: thêm vào `.env.example` (kèm comment) và `backend/app/config.py` nếu backend dùng.

| Biến | Ai dùng | Ý nghĩa |
| --- | --- | --- |
| `LLM_PROVIDER`, `LLM_MODEL`, `MAX_ANSWER_TOKENS` | backend | `mock` \| `ollama`; `LLM_MODEL` vd. `qwen2.5:7b` (model gốc) hoặc `chatbot-hust` (fine-tune) |
| `LLM_BASE_URL`, `LLM_API_KEY` | backend | Địa chỉ Ollama (mặc định `http://localhost:11434/v1`); key chỉ cần khi dùng vLLM có `--api-key` |
| `RETRIEVER`, `TOP_K`, `EMBED_MODEL` | backend, `data/embed_upload.py` | `mock` \| `supabase` |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | backend, `data/` | Dùng **service_role key** |
| `CORS_ORIGINS`, `MIN_SECONDS_BETWEEN_QUESTIONS`, `ADMIN_TOKEN` | backend | |
| `REWRITE_MODEL` | `rag/rewrite.py` (thêm ở T10) | Model Ollama nhỏ để viết lại câu hỏi |
| `MAX_CONCURRENT_ANSWERS`, `MAX_WAITING`, `DAILY_QUESTION_LIMIT` | backend (thêm ở T19) | Giới hạn tải cho máy Mac |
