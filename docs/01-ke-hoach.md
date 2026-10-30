# Kế hoạch dự án

## 1. Làm cái gì

Một trang web chat. Sinh viên hỏi chuyện học vụ ("đăng ký học phần bổ sung thế nào?"), chatbot trả lời ngắn và **ghi rõ lấy từ văn bản nào của trường**.

Đích cuối: chứng minh bằng số liệu là chatbot của nhóm **trả lời đúng ngang hoặc hơn HustVA**, trích nguồn ≥ 90% câu, bịa ít hơn HustVA, và từ chối những câu ngoài phạm vi.

## 2. Bốn phần ghép lại thế nào

```
              ┌──────────── (1) DATA – TV2 ────────────┐
              │ Tải văn bản của trường, làm sạch,       │
              │ cắt thành từng Điều, đưa lên Supabase   │
              └───────────────────┬─────────────────────┘
                                  │ kho văn bản để tìm
                                  ▼
Sinh viên ──► (3) UI + BACKEND – TV4 ──► (2) AI – Khiêm ──► câu trả lời có nguồn [1] [2]
  hỏi         nhận câu hỏi, hiện          tìm đoạn văn bản liên quan,
              câu trả lời từng chữ,       đưa cho model, model viết
              ghi log, chặn spam          câu trả lời kèm số nguồn
                                  ▲
                                  │ điểm số + danh sách câu sai, sai vì đâu
              ┌───────────────────┴─────────────────────┐
              │ (4) EVAL – TV3                          │
              │ Bộ đề 200 câu có đáp án đúng.           │
              │ Hỏi chatbot mình và HustVA, chấm điểm   │
              └─────────────────────────────────────────┘
```

Ba phần trên tạo ra chatbot. Phần Eval **không tạo ra tính năng nào**, nó đo xem chatbot tốt đến đâu.

## 3. Mỗi phần đóng góp gì

| Phần | Người | Làm ra cái gì | Ai dùng | Không có phần này thì |
| --- | --- | --- | --- | --- |
| **Data** | TV2 | Kho văn bản chính thức trên Supabase, mỗi đoạn là một Điều, có tên văn bản, link, ngày hiệu lực | AI tìm trong kho này | Chatbot không có gì để trả lời, hoặc trả lời từ văn bản bẩn, cắt sai |
| **AI / RAG** | Khiêm | Hàm nhận câu hỏi, trả về câu trả lời có trích nguồn. Gồm: tìm đoạn đúng, dựng prompt, gọi model, chặn câu ngoài phạm vi | Backend gọi hàm này | Có kho văn bản nhưng không ai đọc nó để trả lời |
| **Fine-tune** | Khiêm | Một model nhỏ của nhóm, chạy trên máy Mac, thay được model trả tiền (phương án B) | AI dùng thay model API | Vẫn chạy được bằng model API (phương án A). Đây là phần thí nghiệm, không bắt buộc |
| **UI + Backend** | TV4 | Trang web chat, API, log câu hỏi, giới hạn tần suất và chi phí, bản deploy | Sinh viên, Eval | Không ai dùng được chatbot |
| **Eval** | TV3 | Bộ đề + báo cáo điểm sau mỗi lần thay đổi + danh sách câu sai kèm nguyên nhân | Cả nhóm | Không biết chatbot đúng bao nhiêu, không biết sửa gì, không chứng minh được hơn HustVA |

## 4. Eval để làm gì

Eval là **bài kiểm tra** cho chatbot, giống đề thi có đáp án.

1. **Bộ đề:** ~200 câu sinh viên hay hỏi. Mỗi câu có đáp án đúng (lấy từ văn bản của trường) và câu trả lời của HustVA (nhóm hỏi tay rồi chép lại).
2. **Cho chatbot mình làm bài:** script hỏi chatbot từng câu, lưu câu trả lời.
3. **Chấm:** hai model AI làm giám khảo, so câu trả lời của mình và của HustVA với đáp án đúng. Giám khảo không biết câu nào của ai. Người chấm lại những câu hai giám khảo không thống nhất.
4. **Báo cáo:** điểm của mình vs HustVA theo từng chủ đề, và với mỗi câu sai thì sai vì đâu:

| Câu sai vì | Nghĩa là | Gửi cho |
| --- | --- | --- |
| Thiếu dữ liệu | Văn bản trả lời câu đó chưa có trong kho | TV2 (Data) |
| Tìm sai | Văn bản có trong kho, nhưng AI không tìm ra đúng đoạn | Khiêm (AI) |
| Viết sai | Tìm đúng đoạn rồi nhưng model viết sai, thiếu ý hoặc bịa | Khiêm (AI: prompt, model) |

Vì vậy Eval là **vòng lặp cải tiến** của cả nhóm:

```
Data/AI sửa một thứ ──► Eval chạy lại bộ đề ──► điểm tăng? giữ lại : bỏ ──► báo cáo câu sai ──► Data/AI sửa tiếp
```

Mọi PR của Data, AI, Fine-tune đều phải kèm điểm trước/sau. Đến cuối dự án, báo cáo của Eval chính là bằng chứng "tốt hơn HustVA".

## 5. Ba giai đoạn

### Giai đoạn 1 (tuần 1–3): bản chạy đầu tiên

Mục tiêu: hỏi trên web, nhận câu trả lời thật có nguồn cho **một** chủ đề (quy chế đào tạo), và có điểm eval đầu tiên.

| Người | Việc | Task |
| --- | --- | --- |
| TV2 | Lập danh sách nguồn → tải, làm sạch, cắt quy chế → đưa lên Supabase | [T1](13-data.md#t1--bảng-nguồn-tuần-1), [T4](13-data.md#t4--quy-chế-đào-tạo-lên-supabase-tuần-23) |
| Khiêm | Nối AI với Supabase, đo tìm đúng bao nhiêu %, chạy model thật, chỉnh prompt. Thử Colab với dữ liệu đồ chơi | [T5](12-ai-rag.md#t5--nối-supabase-và-đo-recallk-tuần-23), [T6](12-ai-rag.md#t6--phương-án-a-thật-tuần-3), [bước 0](14-finetune.md#t14-bước-0--đi-thử-hết-đường-với-model-đồ-chơi-tuần-3) |
| TV3 | Viết bộ đề 100 câu + đáp án đúng; cả nhóm hỏi HustVA (mỗi người 25 câu) → chạy eval lần đầu | [T2](15-eval.md#t2--bộ-đề-v1-100-câu-tuần-12), [T8](15-eval.md#t8--chạy-eval-lần-đầu-tuần-3) |
| TV4 | Tạo Supabase → hoàn thiện UI → backend ghi log, deploy thử | [T3](11-backend.md#t3--làm-quen-và-tạo-supabase-tuần-1), [T7a](10-ui.md#t7a--đủ-trạng-thái-và-hiển-thị-tuần-23), [T7b](11-backend.md#t7b--nối-thật-và-deploy-thử-tuần-3) |

### Giai đoạn 2 (tuần 4–5): đủ dữ liệu, nâng chất lượng

Mục tiêu: đủ mọi chủ đề, điểm ≥ HustVA.

| Người | Việc | Task |
| --- | --- | --- |
| TV2 | Thêm các nguồn còn lại, kiểm bảng số liệu, script cập nhật tự động | [T9](13-data.md#t9--đủ-nguồn-và-cập-nhật-tự-động-tuần-45) |
| Khiêm | Tìm kiếm tốt hơn (rerank, viết lại câu hỏi), chặn câu ngoài phạm vi. Sinh dữ liệu fine-tune | [T10](12-ai-rag.md#t10--nâng-chất-lượng-truy-xuất-tuần-45), [T13](14-finetune.md#t13--sinh-dataset-sft-tuần-45) |
| TV3 | Kiểm giám khảo AI có chấm giống người không, mở rộng bộ đề lên 200 câu, phân loại câu sai gửi đúng người | [T11](15-eval.md#t11--tin-được-giám-khảo-và-bộ-đề-v2-tuần-45) |
| TV4 | Nút đánh giá Đúng/Sai, trang Giới thiệu, thống kê, kiểm soát chi phí API | [T12a](10-ui.md#t12a--feedback-và-giới-thiệu-tuần-4), [T12b](11-backend.md#t12b--thống-kê-cho-nhóm-tuần-4), [T19](11-backend.md#t19--kiểm-soát-chi-phí-api-tuần-5) |

### Giai đoạn 3 (tuần 6–8): fine-tune, mở cho người dùng, demo

Mục tiêu: bản công khai, có kết luận phương án A vs B, báo cáo cuối.

| Người | Việc | Task |
| --- | --- | --- |
| TV2 | Sửa các văn bản mà eval chỉ ra là thiếu/lỗi, viết báo cáo phần Data | [T17](13-data.md#t17--báo-cáo-phần-data-tuần-8) |
| Khiêm | Guardrails, train model nhỏ, so sánh A/B, chọn model cho demo | [T15](12-ai-rag.md#t15--guardrails-tuần-6), [T14](14-finetune.md#t14--train-lora-và-so-sánh-ab-tuần-67) |
| TV3 | Chạy eval cho model nhỏ, cho 10–20 sinh viên dùng thử, tổng hợp số liệu cuối | [T16b](15-eval.md#t16b--thử-với-người-dùng-thật-tuần-7), [T17](15-eval.md#t17--số-liệu-tổng-tuần-8) |
| TV4 | Deploy công khai, kịch bản demo | [T16a](11-backend.md#t16a--deploy-công-khai-tuần-7), [T18](10-ui.md#t18--kịch-bản-demo-tuần-8) |

Khiêm làm cả AI và Fine-tune, nên AI luôn được ưu tiên. Nếu đến tuần 5 điểm còn thấp, bỏ fine-tune và ghi vào "hướng phát triển" trong báo cáo.

## 6. Checkpoint (họp cuối tuần)

| Cuối tuần | Phải đạt | Chưa đạt thì |
| --- | --- | --- |
| 1 | Ai cũng chạy được bản mock. Có 100 câu hỏi + đáp án HustVA. Có ≥ 10 nguồn. Supabase có bảng. | Dời việc tải dữ liệu sang giữa tuần 2, ưu tiên bộ đề |
| 3 | Hỏi trên web ra câu trả lời thật có nguồn (quy chế). Có báo cáo eval đầu tiên. | Không thêm nguồn mới; cả nhóm sửa phần tìm kiếm |
| 5 | Đủ nguồn. Điểm ≥ HustVA về độ đúng và trích nguồn. | Tuần 6 chỉ sửa lỗi; bỏ fine-tune |
| 7 | Bản công khai. Có kết luận A vs B (hoặc ghi rõ đã bỏ B). | Demo bằng phương án A |

## 7. Ai đang chờ ai

| Người chờ | Chờ cái gì | Từ ai | Hạn |
| --- | --- | --- | --- |
| TV2 | Supabase đã tạo bảng + thông tin kết nối | TV4 | cuối tuần 1 |
| TV3 | Danh sách link văn bản (để ghi nguồn cho đáp án đúng) | TV2 | cuối tuần 1 |
| Khiêm | Bộ đề có ghi nguồn đúng dạng (để đo tìm kiếm) | TV3 | cuối tuần 2 |
| Khiêm | Quy chế đã lên Supabase | TV2 | giữa tuần 3 |
| TV3 | Chatbot chạy thật để chấm | Khiêm | cuối tuần 3 |
| TV4 | Số token mỗi câu (để tính chi phí) | Khiêm | đầu tuần 5 |
| Khiêm | File chunk đủ nguồn (để sinh dữ liệu fine-tune) | TV2 | tuần 5 |

## 8. Thế nào là "xong" một task

- Chạy được trên máy người khác, không chỉ máy mình.
- Đạt mục "Kiểm tra" của task trong file hướng dẫn.
- Đã merge vào `main` qua PR có người review.
- Task của Data, AI, Fine-tune: PR có điểm eval trước/sau.

## 9. Cần chốt trong tuần 1

- Deadline thật? (kế hoạch giả định 8 tuần)
- Giảng viên chấm nặng sản phẩm hay fine-tune? Nếu sản phẩm thì fine-tune làm nhẹ.
- Ngân sách API mỗi tháng? (đề xuất: Khiêm giữ key, gửi riêng từng người)
- Ai có máy Mac chạy model nhỏ? Máy đó phải bật khi chạy eval phương án B và khi demo.
- Tài khoản Colab Pro của ai, lưu checkpoint ở Drive nào?
- Deploy ở đâu? Backend cần ~3 GB RAM (model tìm kiếm), gói miễn phí của Render/Railway không đủ ([11-backend.md, T16a](11-backend.md#t16a--deploy-công-khai-tuần-7)).
