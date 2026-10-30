# Phần Eval – TV3

**Thư mục được sửa:** `eval/` · **Task:** T2, T8, T11, T16b, T17

Việc của bạn: làm **bài kiểm tra** cho chatbot. Bạn không viết tính năng nào, bạn đo chatbot tốt đến đâu.

Phần này phục vụ ba việc:

1. **Chứng minh mục tiêu dự án.** Đích của nhóm là "đúng ngang hoặc hơn HustVA". Câu đó chỉ có giá trị khi có số liệu, và số liệu đó do bạn tạo ra: cùng một bộ đề, hỏi cả hai hệ thống, chấm cùng một cách.
2. **Cho nhóm biết thay đổi nào có ích.** Khiêm đổi prompt, TV2 đổi cách cắt văn bản: điểm tăng thì giữ, giảm thì bỏ. Mọi PR của Data, AI, Fine-tune phải kèm điểm trước/sau do bạn chạy.
3. **Chỉ ra ai cần sửa gì.** Với mỗi câu sai, bạn xác định sai vì **thiếu dữ liệu** (gửi TV2), **tìm sai đoạn** hay **viết sai** (gửi Khiêm).

```
Bộ đề (câu hỏi + đáp án đúng + câu trả lời HustVA)
   ──► hỏi chatbot mình ──► 2 giám khảo AI chấm mình và HustVA ──► báo cáo điểm + câu sai vì đâu ──► gửi TV2 / Khiêm sửa ──► chạy lại
```

Phần của bạn bắt đầu **sớm nhất** (tuần 1), vì không có bộ đề thì không ai đo được gì.

## 1. Đường đi của eval

```
eval/golden/golden_v1.jsonl ──run_eval.py──► eval/results/<thời gian>_<commit>.jsonl ──judge.py──► .judged.jsonl + .report.md
 (câu hỏi + đáp án chuẩn                gọi POST /api/chat?stream=false             JUDGE1 và JUDGE2 chấm "mình" và "HustVA"
  + đáp án HustVA, bạn viết)            của backend đang chạy                       mà không biết câu nào của ai
```

| File | Việc | Ghi chú |
| --- | --- | --- |
| `golden/golden_v1.jsonl` | Bộ đề | Hiện có 3 dòng mẫu `MAU-001..003`. Định dạng: [02-api-contract.md mục 8](02-api-contract.md#8-bộ-đề-evalgoldenjsonl) |
| `run_eval.py --golden <file> --api <url> [--limit N]` | Hỏi backend từng câu | Gửi `session_id: "eval"`. Câu lỗi ghi `error`, không dừng. Tên file kết quả có mã commit hiện tại. |
| `judge.py <file kết quả>` | Chấm | Mỗi câu: đảo ngẫu nhiên vị trí A/B, gọi `judge1` và `judge2`, chấm `correct` 0/1/2, `hallucination`, `cites_source`. Hai giám khảo lệch `correct` → `can_cham_tay: true`. Viết báo cáo tổng + theo chủ đề + danh sách câu mình sai. |
| `common/llm.py` (dùng chung, không sửa) | Gọi model | Đọc `JUDGE1_PROVIDER`, `JUDGE1_MODEL`, `JUDGE1_BASE_URL`, `JUDGE1_API_KEY` (tương tự `JUDGE2_*`) |

`eval/results/` không lên Git. Báo cáo dùng để so sánh thì chép `.report.md` vào `eval/reports/` (tạo thư mục) và commit.

## 2. Cài đặt một lần

```bash
cd eval
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Để chạy `run_eval.py` cần một backend đang chạy (xem README). Trong `.env` ở thư mục gốc đặt `MIN_SECONDS_BETWEEN_QUESTIONS=0`, nếu không backend trả 429 cho mọi câu sau câu đầu.

Thử với mock (không tốn tiền):

```bash
# terminal 1, thư mục backend/
uvicorn app.main:app --port 8000
# terminal 2, thư mục eval/
python run_eval.py --limit 3
```

## 3. Task

### T2 – Bộ đề v1 (100 câu) (tuần 1–2)

**Mục tiêu:** `golden/golden_v1.jsonl` có 100 câu đủ mọi trường, có đáp án HustVA và đáp án chuẩn. Đây là việc rủi ro nhất dự án: trễ thì cả nhóm không đo được gì.

**Các bước (tuần 1):**

1. Gom câu hỏi thật: hỏi bạn bè, đọc câu hay gặp trên các nhóm sinh viên (chỉ lấy nội dung câu hỏi, không lấy tên người hỏi). Nhờ model mạnh gợi thêm câu cho chủ đề còn thiếu.
2. Phân bổ: mỗi chủ đề trong phạm vi (mã ở [02-api-contract.md mục 11](02-api-contract.md#11-mã-chủ-đề-topic)) ít nhất 10 câu; ~15 câu `ngoai_pham_vi` (nấu ăn, giải bài tập, hỏi điểm cá nhân, chính trị...); ~40% `easy`, 40% `medium`, 20% `hard`.
3. Viết lại câu cho giống sinh viên nhắn: viết tắt (đkhp, tc, CPA), thiếu dấu, hỏi cộc lốc. Khoảng 10 câu là câu hỏi tiếp nối ("thế còn học lại thì sao?") — ghi riêng, dùng sau khi `run_eval.py` hỗ trợ `history`.
4. Đặt `id` theo tiền tố chủ đề (`DKHP-001`, `HP-001`...). Xoá 3 dòng `MAU-`.
5. **Thu đáp án HustVA:** chia 100 câu cho 4 người (mỗi người 25). Hỏi tay trên giao diện HustVA, chép nguyên văn vào `hustva_answer`, chụp màn hình lưu Drive, ghi `collected_at` và `collected_by`. **Không viết script tự động hỏi HustVA.** Cách dễ nhất: tạo Google Sheet có cột giống trường JSON, cả nhóm điền, rồi xuất (mục 4).

**Các bước (tuần 2):**

6. Mỗi câu trong phạm vi: tìm trong văn bản chính thức (danh sách URL lấy từ `data/sources.yaml` của TV2), viết `reference_answer` ngắn và `reference_source` **đúng dạng `<url>#Điều <số>`** (url trùng với url trong `sources.yaml`). Khiêm dùng trường này để đo truy xuất tự động, sai dạng là script đo không chạy được.
7. Câu không tìm được văn bản nào: ghi `reference_source: ""` và gửi danh sách cho TV2 để bổ sung nguồn.

**Kiểm tra:** chạy script kiểm định dạng (nhờ agent viết thành `eval/check_golden.py` nếu chưa có):

```bash
python check_golden.py golden/golden_v1.jsonl
```

Script phải kiểm: mỗi dòng là JSON hợp lệ; đủ trường; `id` không trùng; `topic`, `difficulty` đúng mã; câu `in_scope` có `reference_source` khớp regex `^https?://\S+(#Điều \d+)?( ; https?://\S+(#Điều \d+)?)*$`; in số câu theo chủ đề và độ khó.

**Bàn giao:** PR có `golden_v1.jsonl` và `check_golden.py`. Cả nhóm review chéo nội dung (mỗi người đọc 25 câu người khác hỏi).

### T8 – Chạy eval lần đầu (tuần 3)

**Mục tiêu:** có báo cáo đầu tiên so sánh hệ thống mình với HustVA trên chủ đề quy chế.

**Cần trước:** T2, Khiêm báo backend chạy thật được (T6).

**Các bước:**

1. Trong `.env`: cấu hình thật Khiêm gửi (`LLM_PROVIDER`, `LLM_MODEL`, key, `RETRIEVER=supabase`, Supabase), `MIN_SECONDS_BETWEEN_QUESTIONS=0`.
2. Đặt hai giám khảo khác hãng, vd.:
   ```env
   JUDGE1_PROVIDER=anthropic
   JUDGE1_MODEL=claude-opus-5-5
   JUDGE2_PROVIDER=openai_compat
   JUDGE2_MODEL=<model của hãng khác>
   JUDGE2_BASE_URL=<địa chỉ API của hãng đó>
   ```
3. Chạy backend, rồi `curl http://localhost:8000/api/health`: phải thấy đúng provider, model, `retriever: supabase`.
4. `python run_eval.py --limit 5`, mở file trong `results/` xem 5 câu trả lời có hợp lý không. Rồi chạy đủ: `python run_eval.py`.
5. `python judge.py results/<file>.jsonl`. Ước chi phí trước: số câu × 2 giám khảo × ~2.000 token.
6. Mở `.report.md`, xử lý tay các câu `can_cham_tay` (mục 5).
7. Chép báo cáo vào `eval/reports/<ngày>-<cấu hình>.report.md`, ghi ở đầu file: commit, `LLM_MODEL`, `TOP_K`, số câu.

**Kiểm tra:** báo cáo có bảng tổng + bảng theo chủ đề; số câu `LỖI` trong `run_eval` bằng 0.

**Bàn giao:** trình bày báo cáo ở buổi họp cuối tuần 3.

### T11 – Tin được giám khảo và bộ đề v2 (tuần 4–5)

**Mục tiêu:** (1) chứng minh giám khảo LLM chấm khớp người ≥ 85%; (2) bộ đề ~200 câu; (3) mỗi câu sai có nguyên nhân và người chịu trách nhiệm sửa.

**Các bước:**

1. **Chấm tay:** viết `eval/export_manual.py <file .judged.jsonl> --n 40` xuất 40 câu ngẫu nhiên ra CSV với cột `id, question, reference_answer, system_answer, hustva_answer, human_ours, human_hustva`. Chấm `human_*` theo **đúng rubric** trong `RUBRIC` ở `judge.py` (0/1/2). Không nhìn điểm của giám khảo trước khi chấm.
2. Viết `eval/agreement.py <csv> <file .judged.jsonl>`: tính % câu mà điểm người = điểm từng giám khảo. ≥ 85% thì tin được. Thấp hơn: đọc các câu lệch, sửa `RUBRIC` cho rõ hơn, chấm lại, ghi số trước/sau vào PR.
3. **Phân loại lỗi:** viết `eval/classify_errors.py <file .judged.jsonl>`. Với mỗi câu `correct` của mình = 0 hoặc 1:
   - So `reference_source` với `system_sources` (cùng `url`, và `section` chứa đúng `Điều <số>`).
   - Có nguồn đúng trong `system_sources` → **sinh_sai** (gửi Khiêm: prompt/model).
   - Không có, nhưng văn bản có trên Supabase → **truy_xuat_sai** (gửi Khiêm: retriever).
   - `reference_source` rỗng hoặc văn bản chưa có trong `sources.yaml` → **thieu_du_lieu** (gửi TV2).
   - Xuất bảng `eval/reports/<run>-loi.md`: id, câu hỏi, nguyên nhân, người sửa.
4. **Bộ đề v2:** tạo `golden/golden_v2.jsonl` = toàn bộ v1 + ~100 câu mới. Nguồn câu mới: log `chat_logs` của người dùng thật (bỏ thông tin cá nhân), câu hỏi khó mà nhóm phát hiện. Thu đáp án HustVA như T2.

**Kiểm tra:** `python check_golden.py golden/golden_v2.jsonl` không lỗi; có file `agreement` ≥ 85% hoặc giải thích vì sao thấp.

### Chạy eval cho phương án B (tuần 6–7, theo yêu cầu của Khiêm)

Khiêm chạy backend với model fine-tune trên máy Mac. Bạn chạy `python run_eval.py --golden golden/golden_v2.jsonl --api http://<ip-may-mac>:8000` (cùng mạng Wi-Fi), rồi `judge.py`. So hai báo cáo A và B trên **cùng** bộ đề, cùng giám khảo.

### T16b – Thử với người dùng thật (tuần 7)

1. Mời 10–20 sinh viên dùng bản deploy (TV4 gửi link) trong 15 phút.
2. Phiếu hỏi ngắn (Google Form): dễ dùng không (1–5), tin câu trả lời không (1–5), câu nào sai, muốn thêm gì.
3. Câu hỏi hay từ buổi thử: thêm vào bộ đề (thu đáp án HustVA như cũ).

### T17 – Số liệu tổng (tuần 8)

Bảng cuối: mình vs HustVA theo từng chủ đề; phương án A vs B; tỉ lệ từ chối đúng câu ngoài phạm vi; độ trễ trung bình; 3–5 ví dụ đúng/sai tiêu biểu; kết quả phiếu hỏi T16b; giới hạn của cách đo.

## 4. Chuyển Google Sheet sang JSONL

Xuất Sheet thành CSV (`File → Download → CSV`) rồi:

```python
import csv, json
with open("golden.csv", encoding="utf-8") as f, open("golden/golden_v1.jsonl", "w", encoding="utf-8") as out:
    for r in csv.DictReader(f):
        r["in_scope"] = r["in_scope"].strip().lower() in ("true", "1", "có")
        out.write(json.dumps(r, ensure_ascii=False) + "\n")
```

## 5. Xử lý câu `can_cham_tay`

Mở `.judged.jsonl`, tìm dòng `"can_cham_tay": true`, đọc `scores.judge1` và `scores.judge2`, quyết định điểm đúng. Ghi quyết định vào cột riêng trong file chấm tay (không sửa `.judged.jsonl` gốc), và tính lại bảng tổng bằng điểm của người cho các câu này.

## 6. Nguyên tắc để số liệu đáng tin

- **Không sửa bộ đề để làm đẹp điểm.** Thêm câu thì được, xoá câu khó thì không. Sửa câu sai chính tả/đáp án chuẩn sai thì ghi lý do trong PR.
- Bộ đề không được lọt vào dữ liệu fine-tune. `make_sft_dataset.py` tự loại câu giống bộ đề trong `eval/golden/`; khi Khiêm sinh dataset, kiểm lại bằng cách tìm vài câu hỏi bộ đề trong `sft.jsonl`.
- Mỗi lần chạy ghi rõ commit, model, cấu hình. So sánh hai lần chạy chỉ khi cùng bộ đề và cùng giám khảo.
- So sánh với HustVA chỉ trên thông tin công khai; ghi rõ giới hạn này trong báo cáo.
- Log eval vào `chat_logs` với `session_id = 'eval'`. Khi thống kê người dùng thật nhớ loại các dòng này.

## 7. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| Mọi câu sau câu đầu báo `LỖI` 429 | Chưa đặt `MIN_SECONDS_BETWEEN_QUESTIONS=0`, hoặc đặt rồi nhưng chưa khởi động lại backend |
| `run_eval` báo `ConnectError` | Backend chưa chạy, hoặc sai `--api` |
| `judge.py` báo `Chưa đặt JUDGE1_MODEL` | Thiếu biến trong `.env` |
| `judge.py` báo lỗi JSON ở một câu | Giám khảo trả không đúng JSON; câu đó bị đánh `can_cham_tay`. Nhiều câu như vậy thì đổi model giám khảo hoặc hạ `temperature` |
| Câu trả lời mock giống hệt nhau | Đang chạy `LLM_PROVIDER=mock`; kiểm tra `/api/health` |
