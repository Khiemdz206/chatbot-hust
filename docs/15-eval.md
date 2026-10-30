# Hướng dẫn phần Eval

**Người phụ trách:** TV3 · **Thư mục:** `eval/` · **Task:** T2, T8, T11, T16, T17

## 1. Bạn làm gì

Bạn là trọng tài của nhóm. Không có số liệu của bạn thì không ai biết thay đổi nào làm chatbot tốt lên, và không chứng minh được "tốt hơn HustVA". Phần của bạn bắt đầu **sớm nhất** (tuần 1) vì mọi người cần bộ đề để đo.

```
golden/golden_v1.jsonl ──run_eval.py──► results/<lần chạy>.jsonl ──judge.py──► .judged.jsonl + .report.md
  (bộ đề + đáp án HustVA)     gọi /api/chat?stream=false          2 giám khảo LLM chấm, lệch nhau thì người chấm
```

## 2. Cần học trước (khoảng 3–4 giờ)

| Chủ đề | Đủ để làm gì | Tìm với từ khoá |
| --- | --- | --- |
| JSON Lines | Đọc/ghi bộ đề | "jsonl format" |
| Python cơ bản, `httpx` | Chạy script | "httpx quickstart" |
| Đánh giá chatbot, LLM-as-judge | Hiểu điểm mạnh/yếu của việc dùng model chấm | "LLM as a judge bias" |
| Thiết kế bộ đề | Câu hỏi đa dạng, không thiên lệch | "evaluation dataset design RAG" |

## 3. File bạn sở hữu

| File | Nội dung |
| --- | --- |
| `eval/golden/golden_v1.jsonl` | Bộ đề (hiện có 3 dòng mẫu để thấy định dạng) |
| `eval/run_eval.py` | Hỏi hệ thống mình toàn bộ bộ đề |
| `eval/judge.py` | Hai giám khảo LLM chấm mình và HustVA, viết báo cáo |

`eval/results/` không lên Git. Báo cáo `.report.md` quan trọng thì chép vào `eval/reports/` và commit.

## 4. Định dạng một câu trong bộ đề

```json
{"id": "DKHP-007", "topic": "dkhp", "difficulty": "medium", "in_scope": true,
 "question": "đkhp bổ sung muộn có bị phạt k ạ",
 "reference_answer": "Đáp án đúng, ngắn, lấy từ văn bản chính thức",
 "reference_source": "URL văn bản#Điều x khoản y",
 "hustva_answer": "Chép nguyên văn câu trả lời của HustVA",
 "collected_at": "2026-11-05", "collected_by": "TV3"}
```

`topic`: `dkhp`, `hoc_phi`, `diem`, `tot_nghiep`, `hoc_bong`, `thong_bao`, `ngoai_pham_vi`. `difficulty`: `easy` (một câu trong một Điều), `medium` (phải ghép 2 ý), `hard` (nhiều văn bản, có điều kiện, ngoại lệ).

## 5. Việc theo tuần

### Tuần 1 – T2: bộ đề v1 (100 câu) — việc rủi ro nhất dự án
- [ ] Gom câu hỏi thật: hỏi bạn bè, xem câu hỏi hay gặp trên các nhóm sinh viên (chỉ lấy nội dung câu hỏi, không lấy tên người hỏi). Nhờ model mạnh gợi thêm câu cho chủ đề còn thiếu.
- [ ] Phân bổ: mỗi chủ đề ít nhất 12 câu; ~15 câu ngoài phạm vi; khoảng 40% easy, 40% medium, 20% hard.
- [ ] Viết lại câu cho tự nhiên như sinh viên nhắn: có viết tắt, thiếu dấu, hỏi cộc lốc.
- [ ] **Thu đáp án HustVA:** chia đều cho 5 người, mỗi người ~20 câu. Hỏi tay trên giao diện HustVA, chép nguyên văn vào `hustva_answer`, chụp màn hình lưu Drive, ghi ngày hỏi. Không viết script tự động hỏi hệ thống của trường.

**Xong khi:** 100 câu đủ trường, cả nhóm review chéo.

### Tuần 2: đáp án chuẩn
- [ ] Mỗi câu trong phạm vi: tìm trong văn bản chính thức, viết `reference_answer` ngắn + `reference_source` chính xác tới Điều/Khoản.
- [ ] Câu không tìm được văn bản: đánh dấu và hỏi lại Data xem có thiếu nguồn không.

### Tuần 3 – T8: lần chạy đầu
- [ ] Backend chạy với cấu hình thật; trong `.env` đặt `MIN_SECONDS_BETWEEN_QUESTIONS=0`.
- [ ] `python run_eval.py --limit 5` để thử, rồi chạy đủ.
- [ ] Điền `JUDGE1_*`, `JUDGE2_*` trong `.env` (hai model khác hãng), chạy `python judge.py results/<file>.jsonl`.
- [ ] Gửi báo cáo cho nhóm trong buổi họp cuối tuần 3.

### Tuần 4–5 – T11: tin được giám khảo
- [ ] Chấm tay 40 câu ngẫu nhiên theo đúng rubric trong `judge.py`. So với giám khảo: khớp ≥ 85% thì tin được, thấp hơn thì sửa `RUBRIC` và chấm lại.
- [ ] Xử lý các câu `can_cham_tay` (hai giám khảo lệch nhau).
- [ ] Mở rộng bộ đề v2 lên ~200 câu (thêm câu từ log `chat_logs` của người dùng thật, bỏ thông tin cá nhân).
- [ ] Mỗi câu sai, ghi nguyên nhân: **truy xuất sai** (không tìm ra đoạn đúng), **thiếu dữ liệu**, hay **sinh sai** (tìm đúng mà viết sai). Gửi cho đúng người sửa.

### Tuần 7 – T16: người dùng thật
- [ ] Mời 10–20 sinh viên dùng bản deploy 15 phút, phát phiếu hỏi ngắn (dễ dùng không, tin câu trả lời không, câu nào sai).
- [ ] Câu hỏi hay từ buổi thử: thêm vào bộ đề.

### Tuần 8 – T17
- [ ] Bảng số liệu cuối: mình vs HustVA theo từng chủ đề, phương án A vs B, ví dụ câu đúng/sai tiêu biểu.

## 6. Nguyên tắc để số liệu đáng tin

- **Không sửa bộ đề để làm đẹp điểm.** Thêm câu thì được, xoá câu khó thì không.
- Bộ đề không được lọt vào dữ liệu fine-tune (script của Fine-tune đã lọc; vẫn kiểm tra lại).
- Mỗi lần chạy ghi rõ commit, model, cấu hình (tên file kết quả đã kèm commit).
- So sánh với HustVA chỉ trên câu hỏi thông tin công khai; ghi rõ giới hạn này trong báo cáo.

## 7. Bàn giao

- Giao cả nhóm: bộ đề v1 + điểm baseline HustVA (tuần 1–2), báo cáo sau mỗi checkpoint.
- Giao Fine-tune: danh sách câu hỏi eval để loại khỏi dataset (đã tự động qua thư mục `golden/`).
- Giao báo cáo cuối: số liệu tổng (tuần 8).
