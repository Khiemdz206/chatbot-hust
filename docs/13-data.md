# Hướng dẫn phần Data

**Người phụ trách:** TV2 · **Thư mục:** `data/`, `supabase/` (cùng BE) · **Task:** T1, T4, T9

## 1. Bạn làm gì

Đưa văn bản chính thức của trường vào CSDL sao cho tìm được đúng đoạn. Dữ liệu bẩn hoặc cắt sai chỗ là nguyên nhân số một khiến chatbot trả lời sai, nên phần này quan trọng không kém phần AI.

Bốn bước, mỗi bước một script:

```
sources.yaml ──crawl.py──► data/raw/ ──extract.py──► data/clean/ ──chunk.py──► data/chunks/ ──embed_upload.py──► Supabase
 (danh sách)              (file gốc)                (markdown sạch)           (chunks.jsonl)                     (bảng documents, chunks)
```

## 2. Cần học trước (khoảng 5–7 giờ)

| Chủ đề | Đủ để làm gì | Tìm với từ khoá |
| --- | --- | --- |
| HTML, CSS selector | Chọn đúng phần nội dung trên trang | "BeautifulSoup tutorial", "CSS selectors" |
| HTTP, `httpx` | Tải trang/file | "httpx quickstart" |
| Đọc PDF | Trích chữ từ quy chế | "pypdf extract text" |
| Unicode tiếng Việt | Vì sao phải chuẩn hoá NFC | "unicode normalization NFC tiếng Việt" |
| Regex cơ bản | Tách Chương/Điều/Khoản | "python regex tutorial" |
| Supabase | Xem bảng, chạy SQL | "Supabase table editor", "Supabase SQL editor" |

## 3. File bạn sở hữu

| File | Nội dung |
| --- | --- |
| `data/sources.yaml` | Danh sách nguồn (bạn điền) |
| `data/crawl.py` | Tải về `data/raw/`, có đọc robots.txt và nghỉ giữa các lần tải |
| `data/extract.py` | HTML/PDF → markdown sạch trong `data/clean/` |
| `data/chunk.py` | Chia theo Chương → Điều → Khoản |
| `data/embed_upload.py` | Tạo embedding, đưa lên Supabase |
| `data/samples/sample_chunks.jsonl` | Dữ liệu giả cho chế độ mock |

Thư mục `raw/`, `clean/`, `chunks/` không đưa lên Git (quá nặng). Chia sẻ qua Google Drive nhóm nếu cần.

## 4. Chạy thử

```bash
cd data
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python crawl.py && python extract.py && python chunk.py
# Khi đã có SUPABASE_URL và SUPABASE_SERVICE_KEY trong .env:
python embed_upload.py
```

## 5. Việc theo tuần

### Tuần 1 – T1: bảng nguồn
- [ ] Liệt kê nguồn cho từng chủ đề v1: quy chế đào tạo, hướng dẫn đăng ký học phần, quy định học phí, điều kiện tốt nghiệp, học bổng, sổ tay sinh viên, các thông báo trên CTT.
- [ ] Với mỗi nguồn ghi vào `sources.yaml`: URL, loại (html/pdf), chủ đề, ngày hiệu lực, khoá áp dụng.
- [ ] Đánh dấu nguồn nào cần đăng nhập (bỏ ra khỏi v1) và nguồn nào là PDF scan (phải xử lý tay).
- [ ] Hỏi giảng viên/nhóm xem có quy định gì về việc crawl trang của trường không.

**Xong khi:** `sources.yaml` có ít nhất 10 nguồn thật, cả nhóm review.

### Tuần 2–3 – T4: quy chế đào tạo
- [ ] Chạy `crawl.py` cho nguồn quy chế.
- [ ] Chạy `extract.py`, **mở file trong `data/clean/` đọc thử**: còn sót menu, chữ ký, số trang, dòng vỡ không?
- [ ] Trang HTML: tìm khung chứa nội dung chính bằng DevTools (chuột phải → Inspect), sửa `from_html()` để chọn đúng khung đó.
- [ ] Chạy `chunk.py`, đọc 10 chunk ngẫu nhiên: mỗi chunk đứng một mình có hiểu được không, `section` có đúng Điều không.
- [ ] Chạy `embed_upload.py`, mở Supabase kiểm tra bảng `chunks`.

**Xong khi:** quy chế có trên Supabase, 10 chunk kiểm tay đều đúng ranh giới Điều.

### Tuần 4–5 – T9: đủ nguồn và cập nhật tự động
- [ ] Xử lý các nguồn còn lại. Thông báo, tin tức không có Điều thì `chunk.py` tự gom theo đoạn văn.
- [ ] Bảng biểu (học phí, thang điểm) phải giữ nguyên số liệu; kiểm tay từng bảng.
- [ ] Văn bản mới thay văn bản cũ: đặt `is_active = false` cho văn bản cũ trên Supabase thay vì xoá.
- [ ] Viết `update.py` chạy 4 bước liền; chỉ embed lại văn bản có `content_hash` thay đổi (đã có sẵn trong `embed_upload.py`).

## 6. Xử lý PDF scan bằng model mạnh

`extract.py` in "CẦN XỬ LÝ TAY" khi PDF gần như không có lớp chữ. Khi đó:

1. Mở chat với model mạnh nhóm có, đính kèm file PDF.
2. Yêu cầu: *"Chép lại nguyên văn văn bản này dưới dạng markdown. Giữ nguyên Chương, Điều, Khoản, số liệu và bảng. Không tóm tắt, không thêm chữ."*
3. **So từng bảng, từng con số với bản gốc.** Model có thể đọc sai số.
4. Lưu kết quả thành `data/clean/<id>.md`, chép `data/raw/<id>.meta.json` thành `data/clean/<id>.meta.json`.
5. Chạy tiếp `chunk.py`.

## 7. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| Chữ tiếng Việt lỗi kiểu "Ä‘" | Trang không khai báo encoding; thử `r.content.decode("utf-8")` |
| Tìm "Điều 5" không ra dù văn bản có | Văn bản dùng ký tự tổ hợp; kiểm tra đã `unicodedata.normalize("NFC")` |
| Mỗi chunk chỉ vài chữ | Regex nhận nhầm dòng thường thành tiêu đề Điều; in các dòng khớp `RE_DIEU` ra xem |
| `embed_upload.py` rất chậm | Máy không có GPU; chạy file này trên Colab rồi đẩy lên Supabase từ đó |
| Supabase báo sai số chiều vector | `EMBED_MODEL` khác bge-m3; đổi `vector(1024)` trong SQL cho khớp |

## 8. Bàn giao

- Giao cả nhóm: `sources.yaml` (tuần 1).
- Giao AI: quy chế trên Supabase (tuần 2–3), đủ nguồn (tuần 5).
- Giao Fine-tune: `data/chunks/chunks.jsonl` (tuần 4) để sinh dataset.
