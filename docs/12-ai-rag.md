# Hướng dẫn phần AI / RAG

**Người phụ trách:** Khiêm (Lead) · **Thư mục:** `backend/app/rag/` · **Task:** T1, T5, T6, T10, T15

## 1. Bạn làm gì

Phần quyết định chatbot trả lời đúng hay sai: tìm đúng đoạn văn bản, ghép prompt, gọi model, kiểm tra trích dẫn. Mọi thay đổi ở đây phải chạy lại eval trước khi merge.

Hợp đồng với Backend chỉ có một hàm `pipeline.answer(question, history)`. Bên trong `rag/` bạn đổi gì cũng được.

## 2. Cần học trước (khoảng 6–8 giờ)

| Chủ đề | Đủ để làm gì | Tìm với từ khoá |
| --- | --- | --- |
| RAG là gì, vì sao hay sai | Hiểu chỗ cần tối ưu | "RAG failure modes", "retrieval augmented generation tutorial" |
| Embedding, cosine similarity | Hiểu vector search | "sentence-transformers quickstart" |
| pgvector + full-text Postgres | Đọc hàm `match_chunks` | "pgvector hybrid search", "reciprocal rank fusion" |
| Reranker (cross-encoder) | T10 | "bge-reranker", "cross encoder rerank" |
| API Anthropic/OpenAI có stream | Generator | Tài liệu "Messages API streaming", "chat completions stream" |
| Prompt cho RAG | Giảm bịa, bắt trích dẫn | "RAG prompt citations" |

## 3. File bạn sở hữu

| File | Nội dung |
| --- | --- |
| `rag/pipeline.py` | Điều phối: viết lại → tìm → prompt → sinh → nguồn |
| `rag/retriever.py` | `MockRetriever`, `SupabaseRetriever` (gọi hàm SQL `match_chunks`) |
| `rag/prompts.py` | System prompt, cách ghép tài liệu. **Fine-tune dùng chung file này** |
| `rag/generators.py` | Mock, Anthropic, OpenAI-compatible (gồm cả Ollama/vLLM) |

## 4. Pipeline (đích đến cuối tuần 6)

1. **Viết lại câu hỏi** – gộp ngữ cảnh hội thoại ("thế còn học lại?" → câu đầy đủ), mở rộng viết tắt (đkhp, CPA, tc). Dùng model rẻ, nhanh.
2. **Truy xuất hybrid** – ~20 đoạn theo vector + ~20 theo full-text, gộp bằng RRF (đã có trong `match_chunks`).
3. **Rerank** – cross-encoder chấm lại, giữ 5–6 đoạn. Điểm cao nhất dưới ngưỡng thì từ chối luôn, không gọi model sinh.
4. **Dựng prompt** – mỗi đoạn có số `[n]`, tiêu đề, Điều/Khoản, ngày hiệu lực; tài liệu bọc trong `<tai_lieu>`.
5. **Sinh câu trả lời** – qua `Generator`, stream ra từng chữ.
6. **Kiểm tra sau** – không có trích dẫn hợp lệ thì thay bằng câu trả lời an toàn kèm link nguồn gần nhất.

Bản hiện tại đã có bước 2 (một phần), 4, 5. Bước 1, 3, 6 có `TODO` trong code.

## 5. Việc theo tuần

### Tuần 1 – T1 + làm quen
- [ ] Tạo repo trên GitHub từ thư mục này, bật bảo vệ nhánh `main` (xem CONTRIBUTING).
- [ ] Đọc toàn bộ `rag/`, chạy mock, đặt breakpoint trong `pipeline.answer` để thấy dữ liệu đi qua.
- [ ] Cùng Data chốt bảng nguồn và chủ đề v1.
- [ ] Thử `LLM_PROVIDER=anthropic` với dữ liệu mẫu để chắc API key chạy.

### Tuần 2–3 – T5, T6: truy xuất và sinh thật
- [ ] Khi Data đưa quy chế lên Supabase: `RETRIEVER=supabase`, hỏi thử 20 câu chủ đề quy chế.
- [ ] Viết script nhỏ đo **recall@k**: với mỗi câu trong bộ đề có ghi nguồn, đoạn đúng có nằm trong top-k không. Mục tiêu top-5 ≥ 80%.
- [ ] Chỉnh `SYSTEM_PROMPT` cho đến khi: câu trả lời ngắn, có `[n]`, không đủ thông tin thì nói rõ.
- [ ] Ghi lại cấu hình tốt nhất (model, `TOP_K`, prompt) vào PR kèm điểm eval.

**Xong khi:** checkpoint tuần 3 đạt (trả lời thật có nguồn cho chủ đề quy chế, có điểm eval).

### Tuần 4–5 – T10: nâng chất lượng truy xuất
- [ ] Sửa nhánh full-text: câu hỏi dài thì `websearch_to_tsquery` yêu cầu đủ mọi từ nên hay ra rỗng; tách từ khoá và nối bằng OR (sửa trong SQL hoặc tiền xử lý trong Python).
- [ ] Thêm reranker (vd. `BAAI/bge-reranker-v2-m3` qua `sentence_transformers.CrossEncoder`): lấy 20, giữ 6.
- [ ] Cài `rewrite_question()` bằng model rẻ; thêm từ điển viết tắt hay gặp.
- [ ] Mỗi thay đổi: so recall@k và điểm eval trước/sau.

### Tuần 6 – T15: guardrails
- [ ] Câu ngoài phạm vi (nấu ăn, code bài tập...) → từ chối và gợi ý chủ đề hỗ trợ.
- [ ] Không có `[n]` hợp lệ → thay bằng câu trả lời an toàn (bước 6).
- [ ] Thử prompt injection: đặt câu "bỏ qua mọi chỉ dẫn..." vào một chunk mẫu, kiểm tra model không làm theo.
- [ ] Văn bản có `applies_to` → câu trả lời nói rõ áp dụng cho khoá nào.

### Tuần 7: chọn generator cho demo
- [ ] Nhận bảng so sánh A/B từ Fine-tune. Chọn A, B, hoặc B có dự phòng A (B lỗi/hết thời gian thì gọi A).

## 6. Mẹo

- **Sai thì xem truy xuất trước.** Phần lớn câu sai của RAG là do tìm sai đoạn, không phải do model viết kém. Log `chunk_ids` trong `chat_logs` để tra.
- Đổi một thứ mỗi lần, chạy eval, ghi số. Đổi ba thứ cùng lúc thì không biết cái nào có tác dụng.
- Giữ `temperature` thấp (0–0.3) để câu trả lời ổn định.

## 7. Bàn giao

- Nhận từ Data: bảng `chunks` có dữ liệu (tuần 2–3).
- Giao Backend: `pipeline.answer` chạy thật (tuần 3).
- Giao Fine-tune: `prompts.py` ổn định (tuần 4). **Đổi prompt sau đó phải báo Fine-tune**, vì model nhỏ được train theo đúng định dạng này.
