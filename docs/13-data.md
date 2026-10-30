# Phần Data – TV2

**Thư mục được sửa:** `data/`, thêm file mới trong `supabase/migrations/` · **Task:** T1, T4, T9, T17

Việc của bạn: đưa văn bản chính thức của trường vào Supabase sao cho chatbot tìm được đúng đoạn. Chatbot trả lời sai phần lớn vì dữ liệu bẩn hoặc cắt sai chỗ, nên phần này quyết định chất lượng không kém phần AI.

## 1. Đường đi của dữ liệu

```
data/sources.yaml ──crawl.py──► data/raw/ ──extract.py──► data/clean/ ──chunk.py──► data/chunks/chunks.jsonl ──embed_upload.py──► Supabase
 (bạn điền)                  <id>.html|pdf           <id>.md                    (mỗi dòng 1 chunk)                       bảng documents, chunks
                             <id>.meta.json          <id>.meta.json
```

| Script | Đọc | Ghi | Ghi chú |
| --- | --- | --- | --- |
| `crawl.py [--force]` | `sources.yaml` | `raw/<id>.<type>`, `raw/<id>.meta.json` | Bỏ qua nguồn đã tải (trừ `--force`). Đọc robots.txt, nghỉ 2 giây giữa các lần tải. `meta.json` = mục trong yaml + `fetched_at` + `content_hash` (sha256 của file gốc). |
| `extract.py` | `raw/*.meta.json` | `clean/<id>.md`, `clean/<id>.meta.json` | HTML: bỏ `script/style/nav/header/footer/aside/form`, lấy `h1–h4, p, li, tr` trong `<article>` hoặc `<main>` hoặc `<body>`. PDF: `pypdf`. PDF scan: in `CẦN XỬ LÝ TAY` và bỏ qua. Chuẩn hoá Unicode NFC. |
| `chunk.py` | `clean/*.md` + `.meta.json` | `chunks/chunks.jsonl` (ghi đè) | Văn bản có ≥ 2 dòng `Điều <số>`: chia theo Chương → Điều, Điều dài > 2500 ký tự thì cắt theo Khoản. Không có Điều: gom đoạn văn tới ~2500 ký tự. |
| `embed_upload.py` | `chunks/chunks.jsonl` | Supabase `documents`, `chunks` | Gom chunk theo `url`. `content_hash` không đổi thì bỏ qua văn bản đó. Đổi thì upsert `documents`, xoá hết `chunks` cũ của văn bản rồi insert mới. Embed chuỗi `"<title>. <section>\n<content>"` bằng `BAAI/bge-m3` (1024 chiều). |

Định dạng `chunks.jsonl` và bảng Supabase: [02-api-contract.md mục 6, 7](02-api-contract.md#6-datachunkschunksjsonl). Mã `topic`: [mục 11](02-api-contract.md#11-mã-chủ-đề-topic).

`data/raw/`, `data/clean/`, `data/chunks/` không lên Git. Chia sẻ qua Google Drive nhóm khi người khác cần (Khiêm cần `chunks.jsonl` ở T13).

## 2. Cài đặt một lần

```bash
cd data
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Trong `.env` ở thư mục gốc (TV4 gửi riêng sau T3): `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`. Giữ `EMBED_MODEL=BAAI/bge-m3`.

Chạy cả chuỗi:

```bash
python crawl.py && python extract.py && python chunk.py
python embed_upload.py     # lần đầu tải model ~2 GB; máy yếu thì chạy trên Colab (mục 6)
```

## 3. Task

### T1 – Bảng nguồn (tuần 1)

**Mục tiêu:** `data/sources.yaml` có ít nhất 10 nguồn thật, đủ các chủ đề v1.

**Hiện trạng:** `sources.yaml` có 2 mục mẫu (`vi-du-quy-che`, `vi-du-thong-bao`) với URL `example.com`. Comment đầu file giải thích các trường.

**Các bước:**

1. Tìm nguồn cho từng chủ đề: quy chế đào tạo, hướng dẫn đăng ký học phần, quy định học phí, điều kiện tốt nghiệp, học bổng, sổ tay sinh viên, thông báo CTT. Mỗi chủ đề ít nhất 1 nguồn.
2. Mỗi nguồn là **một** văn bản hoặc **một** trang. Thêm một mục vào `sources.yaml`:
   ```yaml
   - id: quy-che-dao-tao-2025          # không dấu, chữ thường, gạch ngang; dùng làm tên file; không đổi sau này
     title: "Quy chế đào tạo đại học"  # tên đầy đủ, sẽ hiện trong danh sách nguồn cho sinh viên
     url: "https://..."                 # link trực tiếp tới file PDF hoặc trang; mỗi nguồn một url khác nhau
     type: pdf                          # html | pdf
     doc_type: quy_che                  # quy_che | thong_bao | so_tay | huong_dan
     topic: quy_che                     # mã ở docs/02-api-contract.md mục 11
     effective_date: "2025-08-01"       # PHẢI để trong ngoặc kép, hoặc null
     applies_to: "K70 trở đi"           # hoặc null
   ```
3. Ghi riêng (trong mô tả PR) các nguồn **không đưa vào v1**: cần đăng nhập, PDF scan quá nhiều trang, ảnh chụp.
4. Hỏi giảng viên xem có quy định gì về việc tải trang của trường không. Ghi câu trả lời vào PR.
5. Xoá 2 mục mẫu khi đã có nguồn thật.

**Kiểm tra:**

```bash
cd data
python -c "import yaml,json; s=yaml.safe_load(open('sources.yaml',encoding='utf-8'))['sources']; json.dumps(s); ids=[x['id'] for x in s]; urls=[x['url'] for x in s]; assert len(ids)==len(set(ids)) and len(urls)==len(set(urls)); print(len(s),'nguồn OK')"
python crawl.py            # mọi nguồn phải ra "đã tải", không có "LỖI"
```

Lệnh thứ nhất báo `TypeError: Object of type date` nghĩa là có ngày chưa để trong ngoặc kép (`crawl.py` sẽ hỏng ở đúng chỗ đó).

**Bàn giao:** PR có `sources.yaml`. Khiêm duyệt. Gửi danh sách URL cho TV3 để viết `reference_source`.

### T4 – Quy chế đào tạo lên Supabase (tuần 2–3)

**Mục tiêu:** quy chế đào tạo nằm trong bảng `chunks`, mỗi chunk đúng một Điều (hoặc một phần Điều), `section` đúng.

**Cần trước:** T1, và TV4 đã chạy migration trên Supabase (T3).

**Hiện trạng:** `extract.py` dòng ~35 có `TODO`: chưa chọn khung nội dung chính của trang CTT, đang lấy cả `<body>` nên có thể dính menu và chân trang.

**Các bước:**

1. `python crawl.py`, rồi `python extract.py`.
2. **Mở từng file `data/clean/<id>.md` và đọc.** Kiểm tra: còn sót menu, chân trang, chữ ký, số trang, dòng bị vỡ giữa câu, chữ lỗi dấu không. Không được bỏ qua bước này.
3. Với trang HTML có rác: mở trang bằng Chrome → chuột phải vào phần nội dung → Inspect → tìm thẻ bao quanh nội dung (vd. `<div class="article-content">`). Sửa `from_html()`:
   ```python
   main = soup.select_one(".article-content") or soup.find("article") or soup.find("main") or soup.body or soup
   ```
   Nếu mỗi trang một kiểu, thêm trường `selector` vào mục trong `sources.yaml` và đọc nó trong `extract.py`.
4. Với PDF có số trang / tiêu đề lặp ở đầu mỗi trang: thêm regex trong `normalize()` hoặc `from_pdf()` để xoá các dòng đó.
5. Với PDF scan: làm theo mục 5.
6. `python chunk.py`. Mỗi văn bản in ra số chunk và kiểu chia (`theo Điều` / `theo đoạn`). Quy chế phải ra `theo Điều`.
7. Đọc 10 chunk ngẫu nhiên:
   ```bash
   python -c "import json,random; rows=[json.loads(l) for l in open('chunks/chunks.jsonl',encoding='utf-8')]; [print(r['section'],'|',len(r['content']),'ký tự\n',r['content'][:300],'\n---') for r in random.sample(rows,10)]"
   ```
   Mỗi chunk đứng một mình phải hiểu được; `section` phải khớp với Điều trong nội dung.
8. `python embed_upload.py`.
9. Vào Supabase → Table Editor → `chunks`: số dòng bằng số chunk; cột `embedding` có giá trị.

**Kiểm tra:** chạy SQL trong Supabase SQL Editor:

```sql
select d.title, count(*) as so_chunk, count(c.embedding) as co_vector
from chunks c join documents d on d.id = c.document_id group by d.title;
```

`so_chunk = co_vector`. Sau đó nhờ Khiêm (hoặc tự làm) chạy backend với `RETRIEVER=supabase`, hỏi "Điều kiện học vượt là gì?": danh sách nguồn phải có Điều đúng.

**Bàn giao:** báo Khiêm "quy chế đã lên Supabase". PR chỉ chứa code (`extract.py`, `chunk.py`...), không chứa dữ liệu. Mô tả PR ghi số văn bản, số chunk, các sửa đổi trong `extract.py`.

### T9 – Đủ nguồn và cập nhật tự động (tuần 4–5)

**Mục tiêu:** mọi nguồn trong `sources.yaml` lên Supabase; một lệnh `python update.py` cập nhật lại tất cả.

**Các bước:**

1. Xử lý từng nguồn còn lại như T4 (bước 2–9).
2. **Bảng biểu** (học phí, thang điểm, điều kiện học bổng): mở `clean/<id>.md`, so **từng con số** với bản gốc. Bảng phải ở dạng `| ô | ô |`, mỗi hàng một dòng. Bảng bị vỡ thì sửa tay file `.md` và ghi lại trong PR.
3. Thông báo, tin tức không có Điều: `chunk.py` tự gom theo đoạn văn. Kiểm tra mỗi chunk có câu đầu nói rõ đây là thông báo gì (nếu không, Khiêm sẽ khó trích nguồn).
4. **Văn bản mới thay văn bản cũ:** không xoá văn bản cũ. Thêm trường `active: false` cho mục cũ trong `sources.yaml`, sửa `embed_upload.py` để gửi `"is_active": src.get("active", True)` (cần mang trường này qua `meta.json` → `chunks.jsonl`). Nhanh hơn thì chạy tay trong SQL Editor:
   ```sql
   update documents set is_active = false where url = '<url văn bản cũ>';
   ```
5. Viết `data/update.py`: chạy lần lượt `crawl.main(force=True)`, `extract.main()`, `chunk.main()`, `embed_upload.main()`; in tóm tắt số văn bản đổi / không đổi. `embed_upload.py` đã tự bỏ qua văn bản có `content_hash` không đổi.
6. Lưu ý: trang HTML có ngày giờ, bộ đếm lượt xem... thì `content_hash` đổi mỗi lần tải dù nội dung không đổi. Nếu gặp, tính hash trên văn bản sạch (`clean/<id>.md`) thay vì file gốc.

**Kiểm tra:** chạy `python update.py` hai lần liên tiếp; lần hai mọi văn bản phải báo `không đổi, bỏ qua`.

**Bàn giao:** báo Khiêm "đủ nguồn v1", gửi `data/chunks/chunks.jsonl` lên Drive cho T13.

### Việc phát sinh (tuần 5–7)

- TV3 gửi danh sách câu sai do **thiếu dữ liệu**: tìm văn bản bổ sung, thêm vào `sources.yaml`.
- Khiêm báo chunk bị cắt sai (vd. một Điều bị chia đôi làm mất ý): chỉnh `MAX_CHARS`, `split_long()` trong `chunk.py`, chạy lại `chunk.py` + `embed_upload.py`, nhờ chạy lại eval.

### T17 – Báo cáo phần Data (tuần 8)

Số văn bản theo chủ đề, số chunk, cách làm sạch, các vấn đề gặp (PDF scan, bảng, văn bản thay thế) và cách xử lý.

## 4. Lệnh SQL hay dùng (Supabase → SQL Editor)

```sql
-- Có bao nhiêu văn bản / chunk
select count(*) from documents; select count(*) from chunks;

-- Xem các chunk của một văn bản
select chunk_index, section, left(content, 120) from chunks
where document_id = (select id from documents where url = '<url>') order by chunk_index;

-- Tìm chunk chứa một cụm từ
select d.title, c.section from chunks c join documents d on d.id = c.document_id
where c.content ilike '%học vượt%';

-- Xoá hẳn một văn bản (chunk tự xoá theo)
delete from documents where url = '<url>';
```

## 5. Xử lý PDF scan bằng model mạnh

`extract.py` in `CẦN XỬ LÝ TAY (PDF scan): <id>` khi PDF gần như không có lớp chữ. Khi đó:

1. Mở chat với model mạnh nhóm có, đính kèm file `data/raw/<id>.pdf`.
2. Yêu cầu: *"Chép lại nguyên văn văn bản này dưới dạng markdown. Mỗi tiêu đề Chương, Điều nằm trên một dòng riêng, bắt đầu bằng 'Chương ...' hoặc 'Điều ...'. Giữ nguyên số liệu và bảng (dạng | ô | ô |). Không tóm tắt, không thêm chữ."*
3. **So từng bảng, từng con số với bản gốc.** Model có thể đọc sai số.
4. Lưu thành `data/clean/<id>.md`, chép `data/raw/<id>.meta.json` thành `data/clean/<id>.meta.json`.
5. Chạy `python chunk.py`. Lưu ý: chạy lại `extract.py` sẽ **không** ghi đè file này (vì nó bỏ qua PDF scan).

## 6. Chạy `embed_upload.py` trên Colab (máy không có GPU, quá chậm)

1. Upload `data/chunks/chunks.jsonl` và `data/embed_upload.py` lên Colab, chọn GPU.
2. Ô 1: `!pip install sentence-transformers supabase python-dotenv`
3. Ô 2: tạo thư mục `chunks/`, đặt `chunks.jsonl` vào; đặt biến môi trường `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` bằng `os.environ[...] = ...` (không lưu notebook có key lên Drive chung).
4. Ô 3: `!python embed_upload.py`

## 7. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| `crawl.py` báo `TypeError: Object of type date is not JSON serializable` | `effective_date` trong yaml chưa để trong ngoặc kép |
| Chữ tiếng Việt lỗi kiểu "Ä‘" | Trang không khai báo encoding; trong `from_html()` dùng `BeautifulSoup(path.read_bytes().decode("utf-8"), ...)` |
| Tìm "Điều 5" không ra dù văn bản có | Văn bản dùng ký tự tổ hợp; kiểm tra đã đi qua `normalize()` (NFC) |
| Quy chế ra `theo đoạn` thay vì `theo Điều` | Dòng "Điều 1." không đứng đầu dòng (PDF dính dòng). Thêm bước tách dòng trước chữ "Điều <số>." trong `normalize()` |
| Mỗi chunk chỉ vài chữ | Regex nhận nhầm dòng thường thành tiêu đề Điều (vd. "Điều 5 của quy chế này..."); in các dòng khớp `RE_DIEU` ra xem, siết regex |
| `embed_upload.py` báo lỗi kích thước request | Văn bản quá nhiều chunk; chia `insert` thành từng lô 100 dòng |
| `embed_upload.py` rất chậm | Chạy trên Colab (mục 6) |
| Supabase báo sai số chiều vector | `EMBED_MODEL` khác bge-m3. Giữ bge-m3; đổi model phải bàn với Khiêm |
| Supabase báo `permission denied` | Đang dùng `anon key`; phải dùng `service_role key` |
