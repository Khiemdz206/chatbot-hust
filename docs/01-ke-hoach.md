# Kế hoạch 8 tuần

Bắt đầu từ tuần 1 (điền ngày thật khi nhóm chốt). Làm theo "lát dọc": hết tuần 3 phải có bản chạy trọn vẹn từ UI tới câu trả lời thật cho **một** chủ đề, rồi mới mở rộng.

Chi tiết từng task (cách làm, tiêu chí xong) nằm trong hướng dẫn của từng phần. File này là bức tranh tổng.

## Mục tiêu đo được

| Tiêu chí | Cách đo | Mục tiêu |
| --- | --- | --- |
| Độ chính xác | Bộ đề ~200 câu, LLM-judge + người chấm | ≥ HustVA |
| Trích nguồn | % câu trả lời có nguồn đúng | ≥ 90% |
| Bịa thông tin | % câu có khẳng định bịa | Thấp hơn HustVA |
| Từ chối đúng | Câu ngoài phạm vi được từ chối | ≥ 90% |
| Độ trễ | Đến chữ đầu tiên | < 3 giây |

Phạm vi v1: quy chế đào tạo, đăng ký học phần, học phí, điểm, tốt nghiệp, học bổng, thông báo CTT. Không gồm dữ liệu cá nhân cần đăng nhập.

## Bảng việc theo tuần

| Tuần | Khiêm (AI) | TV2 (Data) | TV3 (Eval) | TV4 (Fine-tune) | TV5 (UI + BE) |
| --- | --- | --- | --- | --- | --- |
| **1** | Tạo repo, chạy mock, đọc hiểu `rag/`. T1 cùng Data | Học crawl + Supabase. **T1** bảng nguồn | **T2** bộ đề v1 (100 câu) + hỏi HustVA | Học nền LLM/LoRA. **T2** hỗ trợ viết câu hỏi | **T3** chạy mock, làm quen code UI/BE |
| **2** | **T5** nối Supabase, thử embedding | **T4** crawl + làm sạch quy chế | Hoàn thiện bộ đề v1, viết đáp án chuẩn | Hỗ trợ Data kiểm văn bản đã làm sạch | **T7** UI: trạng thái, nguồn, lỗi |
| **3** | **T6** chạy phương án A thật, chỉnh prompt | Chunk + đưa quy chế lên Supabase | **T8** chạy `run_eval` lần đầu | Chạy thử Unsloth với 20 mẫu trên Colab Pro; đo tốc độ Ollama trên Mac | **T7** BE: log vào Supabase, deploy thử |
| **4** | **T10** hybrid + rerank + viết lại câu hỏi | **T9** thêm các nguồn còn lại | **T11** `judge.py`, kiểm judge vs chấm tay | **T13** sinh dataset SFT | **T12** feedback, trang Giới thiệu |
| **5** | Sửa lỗi theo báo cáo eval | **T9** script cập nhật tự động | **T11** bộ đề v2 (200 câu) | **T13** lọc, kiểm tay 5% | **T19** kiểm soát chi phí API; deploy bản ổn định |
| **6** | **T15** guardrails | Xử lý văn bản lỗi eval chỉ ra | Báo cáo lỗi theo chủ đề | **T14** train LoRA trên Colab Pro, xuất GGUF | Cùng bạn có máy Mac chạy Ollama, nối backend |
| **7** | Chọn generator cho demo | Rà soát dữ liệu lần cuối | **T16** thử với 10–20 SV | **T14** so sánh A/B | **T16** deploy công khai |
| **8** | **T18** demo | **T17** báo cáo phần Data | **T17** số liệu tổng | **T17** báo cáo phần FT | **T18** demo |

## Checkpoint (họp cuối tuần)

| Cuối tuần | Phải đạt | Chưa đạt thì |
| --- | --- | --- |
| 1 | Ai cũng chạy được mock. Bộ đề 100 câu có đáp án HustVA. Bảng nguồn xong. | Dời T4 sang giữa tuần 2, ưu tiên bộ đề |
| 3 | Hỏi trên web, nhận câu trả lời thật có nguồn cho chủ đề quy chế. Có điểm eval đầu tiên. | Không mở rộng nguồn; cả nhóm sửa truy xuất |
| 5 | Đủ nguồn v1. Điểm ≥ HustVA ở độ chính xác và trích nguồn. | Tuần 6 tập trung sửa lỗi thay vì guardrails |
| 7 | Bản demo công khai. Có kết luận A vs B. | Demo bằng phương án A, B ghi vào phần "hướng phát triển" |

## Định nghĩa "xong" cho mọi task

- Chạy được trên máy người khác (không chỉ máy mình).
- Đạt tiêu chí nghiệm thu ghi trong hướng dẫn của phần đó.
- Đã merge vào `main` qua PR có người review.
- Task ảnh hưởng chất lượng câu trả lời (AI, Data, Fine-tune): có số eval trước/sau trong PR.

## Câu hỏi nhóm cần chốt trong tuần 1

- Deadline thật là khi nào? (kế hoạch giả định 8 tuần)
- Giảng viên chấm nặng phần sản phẩm hay phần fine-tune? Nếu sản phẩm thì phương án B làm nhẹ.
- Ngân sách API mỗi tháng? Ai giữ API key?
- Ai giữ máy Mac chạy model? Máy đó cần bật suốt các buổi chạy eval và demo.
- Ai giữ tài khoản Colab Pro, và lưu checkpoint ở Google Drive nào?
- Deploy ở đâu? (gợi ý: backend trên Render/Railway gói miễn phí, Supabase gói miễn phí)
