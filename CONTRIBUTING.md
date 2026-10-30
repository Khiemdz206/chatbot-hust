# Làm việc với Git trong nhóm

Hướng dẫn cho người chưa quen làm việc nhóm bằng Git. Làm đúng các bước này thì gần như không bao giờ bị xung đột code lớn.

## Thiết lập một lần

1. Lead tạo repo trên GitHub, mời 4 người còn lại vào **Settings → Collaborators**.
2. Lead bật bảo vệ nhánh: **Settings → Branches → Add rule** cho `main`, tick *Require a pull request before merging* và *Require approvals (1)*.
3. Mỗi người:
   ```bash
   git clone https://github.com/<to-chuc>/chatbot-hust.git
   cd chatbot-hust
   git config user.name "Tên bạn"
   git config user.email "email-github@gmail.com"
   cp .env.example .env
   ```

## Mỗi lần làm một task

```bash
# 1. Lấy code mới nhất
git checkout main
git pull

# 2. Tạo nhánh riêng cho task: <phần>/<mã task>-<mô tả ngắn>
git checkout -b ui/t7-hien-thi-nguon

# 3. Code, chạy thử. Commit nhiều lần nhỏ:
git add web/app.js web/style.css
git commit -m "UI: hiển thị danh sách nguồn dưới câu trả lời"

# 4. Đẩy nhánh lên GitHub
git push -u origin ui/t7-hien-thi-nguon
```

5. Lên GitHub bấm **Compare & pull request**. Trong mô tả PR ghi:
   - Làm task nào (T7)
   - Đã thay đổi gì, chạy thử thế nào
   - Ảnh chụp màn hình (với UI) hoặc kết quả eval trước/sau (với AI, Data, Fine-tune)
6. Nhờ 1 người review. Sửa theo góp ý, push tiếp vào cùng nhánh.
7. Được duyệt thì bấm **Squash and merge**, rồi xoá nhánh.

## Tên nhánh

| Phần | Tiền tố | Ví dụ |
| --- | --- | --- |
| UI | `ui/` | `ui/t7-stream-cau-tra-loi` |
| Backend | `be/` | `be/t12-luu-feedback` |
| AI / RAG | `ai/` | `ai/t10-rerank` |
| Data | `data/` | `data/t4-quy-che-dao-tao` |
| Fine-tune | `ft/` | `ft/t13-sinh-dataset` |
| Eval | `eval/` | `eval/t11-llm-judge` |
| Tài liệu | `docs/` | `docs/cap-nhat-ke-hoach` |

## Khi bị xung đột (conflict)

```bash
git checkout main && git pull
git checkout <nhanh-cua-ban>
git merge main
# Mở các file báo conflict, giữ phần đúng, xoá các dòng <<<<<<< ======= >>>>>>>
git add .
git commit -m "Gộp main vào nhánh"
git push
```

Không chắc giữ phần nào thì hỏi người viết phần kia trong nhóm, đừng xoá bừa.

## Không bao giờ commit

- File `.env` và mọi API key. Lỡ commit: báo Lead ngay để **đổi key**, xoá khỏi lịch sử không đủ.
- Dữ liệu crawl (`data/raw`, `data/clean`), file model (`.gguf`, thư mục LoRA): quá nặng, đã có trong `.gitignore`. Chia sẻ qua Google Drive của nhóm.

## Họp nhóm

- **Đầu tuần (15 phút):** mỗi người nói tuần này làm task nào, cần ai hỗ trợ.
- **Cuối tuần (30 phút):** demo, xem báo cáo eval, cập nhật `docs/01-ke-hoach.md`.
- Bị kẹt quá 1 buổi thì hỏi ngay trong nhóm chat, đừng chờ đến họp.
