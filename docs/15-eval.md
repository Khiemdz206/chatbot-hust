# Phần Eval – TV3

**Thư mục được sửa:** `eval/` · **Task:** T2, T8, T11, T16b, T17

Việc của bạn: làm **bài kiểm tra** cho chatbot. Bạn không viết tính năng nào, bạn đo chatbot tốt đến đâu.

Phần này phục vụ ba việc:

1. **Chứng minh mục tiêu dự án.** Đích của nhóm là "đúng ngang hoặc hơn HustVA". Câu đó chỉ có giá trị khi có số liệu, và số liệu đó do bạn tạo ra: cùng một bộ đề, hỏi cả hai hệ thống, chấm cùng một cách.
2. **Cho nhóm biết thay đổi nào có ích.** Khiêm đổi prompt hay train model mới, TV2 đổi cách cắt văn bản: điểm tăng thì giữ, giảm thì bỏ. Mọi PR của Data, AI, Fine-tune phải kèm điểm trước/sau do bạn chạy. Quan trọng nhất: chứng minh **model fine-tune hơn model gốc**.
3. **Chỉ ra ai cần sửa gì.** Với mỗi câu sai, bạn xác định sai vì **thiếu dữ liệu** (gửi TV2), **tìm sai đoạn** hay **viết sai** (gửi Khiêm).

Giám khảo là **AI agent của bạn**, không gọi API. Script chuẩn bị đề, chia lô và kiểm tra kết quả; agent đọc từng câu và chấm. Cách làm từng bước: [mục 4](#4-chấm-điểm-bằng-ai-agent-từng-bước).

## 1. Đường đi của eval

```
golden/golden_v1.jsonl ──run_eval.py──► results/<run>.jsonl
 (câu hỏi + đáp án chuẩn      hỏi chatbot qua           │
  + câu trả lời HustVA)       POST /api/chat            ▼
                                     judge.py prepare ──► <run>.judge_tasks.jsonl (A/B đảo ngẫu nhiên)
                                                        │   + <run>.judge_key.json (A/B nào của ai)
                                                        ▼
                                     judge.py status  ──► in lời nhắn giao lô 25 câu cho agent
                                                        ▼
                                     agent đọc RUBRIC.md, chấm ──► <run>.judge_scores.jsonl
                                                        │   (lặp status → agent đến khi đủ)
                                     judge.py report  ──► <run>.judged.jsonl + <run>.report.md
```

| File | Việc | Ghi chú |
| --- | --- | --- |
| `golden/golden_v1.jsonl` | Bộ đề | Hiện có 3 dòng mẫu `MAU-001..003`. Định dạng: [02-api-contract.md mục 8](02-api-contract.md#8-bộ-đề-evalgoldenjsonl) |
| `run_eval.py --golden <file> --api <url> [--limit N]` | Hỏi chatbot từng câu | Gửi `session_id: "eval"`. Câu lỗi ghi `error`, không dừng. Tên file kết quả có mã commit hiện tại |
| `judge.py prepare <file kết quả>` | Tạo đề cho giám khảo | Mỗi câu: câu trả lời của mình và HustVA đặt ngẫu nhiên vào A/B để giám khảo không biết của ai |
| `judge.py status <file kết quả> [--paste]` | Giao lô và kiểm tra | Đếm câu đã chấm, báo dòng agent ghi sai định dạng, in sẵn lời nhắn giao lô tiếp theo |
| `RUBRIC.md` | Hướng dẫn chấm cho agent | `correct` 0/1/2, `hallucination`, `cites_source`, `note`, `unsure`. Muốn đổi cách chấm thì sửa file này |
| `judge.py report <file kết quả>` | Gom điểm, viết báo cáo | Câu `unsure` hoặc chưa được chấm → `can_cham_tay: true`. Báo cáo: bảng tổng, theo chủ đề, danh sách câu mình sai |

`eval/results/` không lên Git. Báo cáo dùng để so sánh thì chép `.report.md` vào `eval/reports/` (tạo thư mục) và commit.

## 2. Cài đặt một lần

```bash
cd eval
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`run_eval.py` cần một backend đang chạy. Bạn có hai cách:
- Gọi backend trên máy Mac của nhóm (cùng Wi-Fi): `--api http://<ip-cua-mac>:8000`. Cách này dùng đúng model thật.
- Chạy backend mock trên máy mình (xem README) để thử script.

Backend phải đặt `MIN_SECONDS_BETWEEN_QUESTIONS=0` trong `.env`, nếu không mọi câu sau câu đầu bị 429. Với model local, mỗi câu mất 5–20 giây, 200 câu khoảng 30–60 phút.

Thử với mock:

```bash
# terminal 1, thư mục backend/
uvicorn app.main:app --port 8000
# terminal 2, thư mục eval/
python run_eval.py --limit 3
python judge.py prepare results/<file vừa tạo>.jsonl
python judge.py status results/<file vừa tạo>.jsonl
```

## 3. Task

### T2 – Bộ đề v1 (100 câu) (tuần 1–2)

**Mục tiêu:** `golden/golden_v1.jsonl` có 100 câu đủ mọi trường, có đáp án HustVA và đáp án chuẩn. Đây là việc rủi ro nhất dự án: trễ thì cả nhóm không đo được gì.

**Các bước (tuần 1):**

1. Gom câu hỏi thật: hỏi bạn bè, đọc câu hay gặp trên các nhóm sinh viên (chỉ lấy nội dung câu hỏi, không lấy tên người hỏi). Nhờ agent gợi thêm câu cho chủ đề còn thiếu.
2. Phân bổ: mỗi chủ đề trong phạm vi (mã ở [02-api-contract.md mục 11](02-api-contract.md#11-mã-chủ-đề-topic)) ít nhất 10 câu; ~15 câu `ngoai_pham_vi` (nấu ăn, giải bài tập, hỏi điểm cá nhân, chính trị...); ~40% `easy`, 40% `medium`, 20% `hard`.
3. Viết lại câu cho giống sinh viên nhắn: viết tắt (đkhp, tc, CPA), thiếu dấu, hỏi cộc lốc.
4. Đặt `id` theo tiền tố chủ đề (`DKHP-001`, `HP-001`...). Xoá 3 dòng `MAU-`.
5. **Thu đáp án HustVA:** chia 100 câu cho 4 người (mỗi người 25). Hỏi tay trên giao diện HustVA, chép nguyên văn vào `hustva_answer`, chụp màn hình lưu Drive, ghi `collected_at` và `collected_by`. **Không viết script tự động hỏi HustVA.** Cách dễ nhất: tạo Google Sheet có cột giống trường JSON, cả nhóm điền, rồi chuyển sang JSONL (mục 5).

**Các bước (tuần 2):**

6. Mỗi câu trong phạm vi: tìm trong văn bản chính thức (danh sách URL lấy từ `data/sources.yaml` của TV2), viết `reference_answer` ngắn và `reference_source` **đúng dạng `<url>#Điều <số>`** (url trùng với url trong `sources.yaml`). Khiêm dùng trường này để đo truy xuất tự động, sai dạng thì script đo không chạy được.
7. Câu không tìm được văn bản nào: ghi `reference_source: ""` và gửi danh sách cho TV2 để bổ sung nguồn.

**Kiểm tra:** nhờ agent viết `eval/check_golden.py`, rồi chạy:

```bash
python check_golden.py golden/golden_v1.jsonl
```

Script phải kiểm: mỗi dòng là JSON hợp lệ; đủ trường; `id` không trùng; `topic`, `difficulty` đúng mã; câu `in_scope` có `reference_source` khớp regex `^https?://\S+(#Điều \d+)?( ; https?://\S+(#Điều \d+)?)*$`; in số câu theo chủ đề và độ khó.

**Bàn giao:** PR có `golden_v1.jsonl` và `check_golden.py`. Cả nhóm review chéo nội dung (mỗi người đọc 25 câu người khác hỏi).

### T8 – Chạy eval lần đầu (tuần 3)

**Mục tiêu:** báo cáo đầu tiên so sánh chatbot (đang chạy **model gốc** qua Ollama) với HustVA trên chủ đề quy chế. Đây là mốc để sau này đo model fine-tune.

**Cần trước:** T2; Khiêm báo backend trên Mac chạy thật được (T6).

**Các bước:**

1. `curl http://<ip-cua-mac>:8000/api/health`: phải thấy `llm_provider: ollama`, đúng `llm_model`, `retriever: supabase`.
2. `python run_eval.py --api http://<ip-cua-mac>:8000 --limit 5`, mở file trong `results/` xem 5 câu trả lời có hợp lý không. Rồi chạy đủ.
3. Chấm bằng AI agent theo đúng [mục 4](#4-chấm-điểm-bằng-ai-agent-từng-bước): `prepare` → lặp `status` + giao lô cho agent → `report`.
4. Xử lý các câu `can_cham_tay` (mục 6).
5. Chép báo cáo vào `eval/reports/<ngày>-<model>.report.md`, ghi ở đầu file: commit, `LLM_MODEL`, `TOP_K`, số câu.

**Kiểm tra:** báo cáo có bảng tổng + bảng theo chủ đề; không còn câu `LỖI` trong `run_eval`.

**Bàn giao:** trình bày báo cáo ở buổi họp cuối tuần 3.

### T11 – Tin được giám khảo và bộ đề v2 (tuần 4–5)

**Mục tiêu:** (1) chứng minh agent chấm khớp người ≥ 85%; (2) bộ đề ~200 câu; (3) mỗi câu sai có nguyên nhân và người chịu trách nhiệm sửa.

**Các bước:**

1. **Chấm tay:** nhờ agent viết `eval/export_manual.py <file .judged.jsonl> --n 40`: xuất 40 câu ngẫu nhiên ra CSV với cột `id, question, reference_answer, system_answer, hustva_answer, human_ours, human_hustva`. Bạn chấm `human_*` theo **đúng** `RUBRIC.md` (0/1/2), không nhìn điểm của agent trước.
2. Nhờ agent viết `eval/agreement.py <csv> <file .judged.jsonl>`: tính % câu mà điểm người = điểm agent. ≥ 85% thì tin được. Thấp hơn: đọc các câu lệch, sửa `RUBRIC.md` cho rõ, chấm lại, ghi số trước/sau vào PR.
3. **Phân loại lỗi:** nhờ agent viết `eval/classify_errors.py <file .judged.jsonl>`. Với mỗi câu `correct` của mình = 0 hoặc 1:
   - So `reference_source` với `system_sources` (cùng `url`, `section` chứa đúng `Điều <số>`).
   - Có nguồn đúng trong `system_sources` → **sinh_sai** (gửi Khiêm: prompt/model).
   - Không có, nhưng văn bản có trên Supabase → **truy_xuat_sai** (gửi Khiêm: retriever).
   - `reference_source` rỗng hoặc văn bản chưa có trong `sources.yaml` → **thieu_du_lieu** (gửi TV2).
   - Xuất bảng `eval/reports/<run>-loi.md`: id, câu hỏi, nguyên nhân, người sửa.
4. **Bộ đề v2:** `golden/golden_v2.jsonl` = toàn bộ v1 + ~100 câu mới (từ `chat_logs` của người dùng thật, bỏ thông tin cá nhân; câu khó nhóm phát hiện). Thu đáp án HustVA như T2.

**Kiểm tra:** `python check_golden.py golden/golden_v2.jsonl` không lỗi; agreement ≥ 85% hoặc có giải thích vì sao thấp.

### So sánh model gốc và model fine-tune (tuần 5–6, theo yêu cầu của Khiêm)

Mỗi khi Khiêm có model mới, chạy eval hai lần trên **cùng bộ đề**: một lần backend đặt `LLM_MODEL=<model gốc>`, một lần `LLM_MODEL=chatbot-hust`. Chấm bằng cùng `RUBRIC.md`. Gửi Khiêm bảng: điểm đúng, % trích nguồn, % bịa, % từ chối đúng câu ngoài phạm vi, độ trễ trung bình (`latency_ms`).

### T16b – Thử với người dùng thật (tuần 7)

1. Mời 10–20 sinh viên dùng bản công khai (TV4 gửi link) trong 15 phút.
2. Phiếu hỏi ngắn (Google Form): dễ dùng không (1–5), tin câu trả lời không (1–5), câu nào sai, muốn thêm gì.
3. Câu hỏi hay từ buổi thử: thêm vào bộ đề (thu đáp án HustVA như cũ).

### T17 – Số liệu tổng (tuần 8)

Bảng cuối: mình vs HustVA theo từng chủ đề; model gốc vs fine-tune; tỉ lệ từ chối đúng câu ngoài phạm vi; độ trễ trung bình; 3–5 ví dụ đúng/sai tiêu biểu; kết quả phiếu hỏi T16b; giới hạn của cách đo (một giám khảo AI, đã kiểm bằng chấm tay).

## 4. Chấm điểm bằng AI agent: từng bước

Làm sau mỗi lần chạy `run_eval.py`. 200 câu = 8 lô × 25 câu, mất khoảng 1–2 giờ. Mọi lệnh chạy trong thư mục `eval/`.

### 4.1. Chọn cách làm

| Cách | Dùng khi | Bạn làm gì |
| --- | --- | --- |
| **A. Agent đọc/ghi file** (khuyên dùng) | Bạn dùng AI agent lập trình mở được thư mục repo | Gửi lời nhắn script in ra; agent tự đọc đề và tự ghi điểm vào file |
| **B. AI chỉ chat** | AI của bạn chỉ có khung chat, không đọc/ghi file | Dán đề vào chat, chép kết quả AI trả về dán vào file |

**Giữ cùng một AI và cùng một model** cho mọi lần chạy cần so với nhau (vd. model gốc vs model fine-tune). Đổi giám khảo giữa chừng thì hai con số không so được. Ghi tên AI/model giám khảo vào đầu báo cáo.

### 4.2. Chuẩn bị đề (một lần cho mỗi lần chạy)

```bash
python judge.py prepare results/<run>.jsonl
```

Script tạo 2 file cạnh file kết quả:
- `<run>.judge_tasks.jsonl`: đề cho agent. Mỗi câu có câu hỏi, đáp án chuẩn, và hai câu trả lời `A`, `B`: một của chatbot mình, một của HustVA, đảo ngẫu nhiên.
- `<run>.judge_key.json`: A/B nào là của ai. **Agent không được mở file này.**

Không chạy `prepare` hai lần cho cùng một lần chạy (A/B sẽ đảo khác, điểm cũ thành sai). Script tự chặn nếu đã có điểm.

### 4.3. Chấm từng lô – cách A (agent đọc/ghi file)

1. Mở một **phiên agent mới** ở thư mục gốc repo. Phiên mới nghĩa là agent chưa đọc code chatbot hay file kết quả, nên không đoán được câu nào của nhóm.
2. Chạy:
   ```bash
   python judge.py status results/<run>.jsonl
   ```
   Script in số câu đã chấm, rồi in một lời nhắn nằm giữa hai đường kẻ `=====`, dạng:
   > Đọc file eval/RUBRIC.md và làm đúng theo đó. Chấm các câu có id sau trong file eval/results/<run>.judge_tasks.jsonl: DKHP-001, DKHP-002, ... Ghi kết quả nối tiếp vào cuối file eval/results/<run>.judge_scores.jsonl ...
3. Chép nguyên đoạn đó, gửi cho agent. Chờ agent báo xong.
4. Chạy lại `status`. Kiểm tra:
   - "Đã chấm hợp lệ" tăng đúng bằng số câu vừa giao (thường 25).
   - Không có dòng "sai định dạng". Nếu có: nhắn agent *"Dòng X trong file eval/results/<run>.judge_scores.jsonl sai: <lý do status in ra>. Sửa lại đúng định dạng trong RUBRIC.md."* Hoặc xoá dòng đó, câu đó sẽ tự quay lại ở lô sau.
5. Mở file `<run>.judge_scores.jsonl`, đọc 3 dòng cuối: `note` có khớp với câu hỏi không. Thấy agent chấm bừa (câu nào cũng 2 điểm, `note` giống hệt nhau) thì xoá các dòng của lô đó, mở phiên mới và giao lại.
6. Lặp lại bước 2–5 đến khi `status` báo **"Đã chấm đủ"**. Cứ 3–4 lô thì mở phiên agent mới, vì phiên dài agent dễ chấm qua loa.

### 4.4. Chấm từng lô – cách B (AI chỉ chat)

1. Mở một cuộc chat mới.
2. Chạy:
   ```bash
   python judge.py status results/<run>.jsonl --paste > lo.txt
   ```
   Mở `lo.txt`, chép phần giữa hai đường kẻ `=====` (gồm rubric và 25 câu), dán vào chat.
3. AI trả về 25 dòng JSON. Chép hết, mở `eval/results/<run>.judge_scores.jsonl` bằng trình soạn thảo (tạo file mới nếu chưa có), dán vào **cuối** file, lưu.
4. Kiểm tra như cách A bước 4–5, lặp đến khi đủ.

### 4.5. Ra báo cáo

```bash
python judge.py report results/<run>.jsonl
```

Tạo `<run>.report.md`: độ chính xác, % trích nguồn, % bịa của mình và HustVA, theo từng chủ đề, và danh sách câu mình sai. Còn cảnh báo "chưa được chấm" thì quay lại 4.3. Sau đó xử lý câu `can_cham_tay` (mục 6) và chép báo cáo vào `eval/reports/`.

### 4.6. Vì sao tin được điểm của agent

- Agent không biết câu trả lời nào của nhóm: A/B đảo ngẫu nhiên, khoá giấu ở file riêng, chấm bằng phiên mới.
- Mình và HustVA được chấm cùng một rubric, cùng một giám khảo.
- Ở T11 bạn tự chấm tay 40 câu và so với agent. Khớp ≥ 85% thì ghi con số đó vào báo cáo cuối làm bằng chứng.

## 5. Chuyển Google Sheet sang JSONL

Xuất Sheet thành CSV (`File → Download → CSV`) rồi:

```python
import csv, json
with open("golden.csv", encoding="utf-8") as f, open("golden/golden_v1.jsonl", "w", encoding="utf-8") as out:
    for r in csv.DictReader(f):
        r["in_scope"] = r["in_scope"].strip().lower() in ("true", "1", "có")
        out.write(json.dumps(r, ensure_ascii=False) + "\n")
```

## 6. Xử lý câu `can_cham_tay`

Mở `.judged.jsonl`, tìm dòng `"can_cham_tay": true`. Câu chưa được chấm: chạy `status` để giao lại cho agent. Câu `unsure`: đọc `scores.ours.note`, `scores.hustva.note`, tự quyết định điểm. Ghi quyết định vào file chấm tay (không sửa `.judged.jsonl` gốc) và tính lại bảng tổng bằng điểm của người cho các câu này.

## 7. Nguyên tắc để số liệu đáng tin

- **Không sửa bộ đề để làm đẹp điểm.** Thêm câu thì được, xoá câu khó thì không. Sửa câu sai chính tả/đáp án chuẩn sai thì ghi lý do trong PR.
- **Giám khảo không được biết câu nào của ai:** dùng phiên agent mới để chấm, không cho nó mở `*.judge_key.json` hay file kết quả gốc.
- Bộ đề không được lọt vào dữ liệu fine-tune. `make_sft_dataset.py` tự loại câu giống bộ đề trong `eval/golden/`; khi Khiêm sinh dataset, kiểm lại bằng cách tìm vài câu hỏi bộ đề trong `sft.jsonl`.
- Mỗi lần chạy ghi rõ commit, model, cấu hình. So sánh hai lần chạy chỉ khi cùng bộ đề và cùng rubric.
- So sánh với HustVA chỉ trên thông tin công khai; ghi rõ giới hạn này trong báo cáo.
- Log eval vào `chat_logs` với `session_id = 'eval'`. Khi thống kê người dùng thật nhớ loại các dòng này.

## 8. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| `UnicodeEncodeError: 'charmap'` trên Windows | `set PYTHONUTF8=1` (cmd) hoặc `$env:PYTHONUTF8=1` (PowerShell) trước khi chạy |
| Mọi câu sau câu đầu báo `LỖI` 429 | Backend chưa đặt `MIN_SECONDS_BETWEEN_QUESTIONS=0`, hoặc đặt rồi nhưng chưa khởi động lại |
| `run_eval` báo `ConnectError` | Backend chưa chạy, sai `--api`, hoặc Wi-Fi chặn kết nối tới Mac (dùng hotspot) |
| `run_eval` báo timeout | Model local chậm; câu trả lời quá dài. Báo Khiêm |
| `report` báo câu chưa được chấm | Agent bỏ sót; chạy `status`, giao lô tiếp theo (script tự chọn các câu còn thiếu) |
| `status` báo dòng sai định dạng | Agent ghi `"2"` thay vì `2`, thiếu trường, hoặc bọc trong khối code; xem mục 4.3 bước 4 |
| `prepare` báo đã có file điểm | Lần chạy này đã chuẩn bị rồi; dùng `status` để chấm tiếp. Muốn chấm lại từ đầu thì xoá `<run>.judge_scores.jsonl` |
| Agent nói không đọc được file | Agent không mở ở thư mục repo, hoặc chỉ chat được: dùng cách B (mục 4.4) |
| Câu trả lời giống hệt nhau | Backend đang chạy `LLM_PROVIDER=mock`; kiểm tra `/api/health` |
