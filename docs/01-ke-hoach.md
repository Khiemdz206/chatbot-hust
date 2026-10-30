# Kế hoạch dự án

## 1. Làm cái gì

Một trang web chat. Sinh viên hỏi chuyện học vụ ("đăng ký học phần bổ sung thế nào?"), chatbot trả lời ngắn và **ghi rõ lấy từ văn bản nào của trường**.

Chatbot chạy bằng **model nhỏ nhóm tự fine-tune, chạy local bằng Ollama trên máy Mac**, không gọi API model trả tiền.

Đích cuối: chứng minh bằng số liệu là chatbot của nhóm **trả lời đúng ngang hoặc hơn HustVA**, trích nguồn ≥ 90% câu, bịa ít hơn HustVA, từ chối những câu ngoài phạm vi, và model fine-tune **tốt hơn model gốc** chưa fine-tune.

## 2. Bốn phần ghép lại thế nào

```
              ┌──────────── (1) DATA – TV2 ────────────┐
              │ Tải văn bản của trường, làm sạch,       │
              │ cắt thành từng Điều, đưa lên Supabase   │
              └───────────────────┬─────────────────────┘
                                  │ kho văn bản để tìm
                                  ▼
Sinh viên ──► (3) UI + BACKEND – TV4 ──► (2) AI + FINE-TUNE – Khiêm ──► câu trả lời có nguồn [1] [2]
  hỏi         nhận câu hỏi, hiện          tìm đoạn văn bản liên quan,
              câu trả lời từng chữ,       đưa cho model nhóm tự fine-tune
              ghi log, chặn quá tải       (chạy bằng Ollama), model viết câu trả lời
                                  ▲
                                  │ điểm số + danh sách câu sai, sai vì đâu
              ┌───────────────────┴─────────────────────┐
              │ (4) EVAL – TV3                          │
              │ Bộ đề 200 câu có đáp án đúng.           │
              │ Hỏi chatbot mình và HustVA, chấm điểm   │
              └─────────────────────────────────────────┘

Cả backend và Ollama chạy trên máy Mac của nhóm. Mở ra ngoài bằng Cloudflare Tunnel.
```

Ba phần trên tạo ra chatbot. Phần Eval **không tạo ra tính năng nào**, nó đo xem chatbot tốt đến đâu.

## 3. Mỗi phần đóng góp gì

| Phần | Người | Làm ra cái gì | Ai dùng | Không có phần này thì |
| --- | --- | --- | --- | --- |
| **Data** | TV2 | Kho văn bản chính thức trên Supabase, mỗi đoạn là một Điều, có tên văn bản, link, ngày hiệu lực | AI tìm trong kho; Fine-tune lấy các đoạn này làm nguyên liệu dữ liệu train | Chatbot không có gì để trả lời, hoặc trả lời từ văn bản bẩn, cắt sai |
| **AI / RAG** | Khiêm | Hàm nhận câu hỏi, trả về câu trả lời có trích nguồn. Gồm: tìm đoạn đúng, dựng prompt, gọi model, chặn câu ngoài phạm vi | Backend gọi hàm này | Có kho văn bản nhưng không ai đọc nó để trả lời |
| **Fine-tune** | Khiêm (agent cả nhóm viết dữ liệu) | Model `chatbot-hust`: model nhỏ đã học cách trả lời ngắn, có `[n]`, biết nói "chưa tìm thấy" | AI dùng làm model sinh câu trả lời | Chỉ có model gốc: hay quên trích nguồn, trả lời lan man, bịa nhiều hơn |
| **UI + Backend** | TV4 | Trang web chat, API, log câu hỏi, giới hạn tải cho máy Mac, bản mở công khai | Sinh viên, Eval | Không ai dùng được chatbot |
| **Eval** | TV3 | Bộ đề + báo cáo điểm sau mỗi lần thay đổi + danh sách câu sai kèm nguyên nhân | Cả nhóm | Không biết chatbot đúng bao nhiêu, không biết fine-tune có ích không, không chứng minh được hơn HustVA |

**Việc của AI agent:** mỗi người dùng AI agent của mình. Ngoài việc giúp code, agent còn làm hai việc thay cho API:
- viết dữ liệu train cho model nhỏ (theo `finetune/TEACHER.md`, cả nhóm chia lô làm);
- làm giám khảo chấm điểm eval (theo `eval/RUBRIC.md`).

## 4. Eval để làm gì

Eval là **bài kiểm tra** cho chatbot, giống đề thi có đáp án.

1. **Bộ đề:** ~200 câu sinh viên hay hỏi. Mỗi câu có đáp án đúng (lấy từ văn bản của trường) và câu trả lời của HustVA (nhóm hỏi tay rồi chép lại).
2. **Cho chatbot mình làm bài:** script hỏi chatbot từng câu, lưu câu trả lời.
3. **Chấm:** AI agent làm giám khảo, so câu trả lời của mình và của HustVA với đáp án đúng. Giám khảo không biết câu nào của ai. Người chấm tay 40 câu để kiểm giám khảo có chấm giống người không.
4. **Báo cáo:** điểm của mình vs HustVA theo từng chủ đề, và với mỗi câu sai thì sai vì đâu:

| Câu sai vì | Nghĩa là | Gửi cho |
| --- | --- | --- |
| Thiếu dữ liệu | Văn bản trả lời câu đó chưa có trong kho | TV2 (Data) |
| Tìm sai | Văn bản có trong kho, nhưng AI không tìm ra đúng đoạn | Khiêm (AI) |
| Viết sai | Tìm đúng đoạn rồi nhưng model viết sai, thiếu ý hoặc bịa | Khiêm (prompt, fine-tune) |

Vì vậy Eval là **vòng lặp cải tiến** của cả nhóm:

```
Data/AI/Fine-tune sửa một thứ ──► Eval chạy lại bộ đề ──► điểm tăng? giữ lại : bỏ ──► báo cáo câu sai ──► sửa tiếp
```

Hai so sánh quan trọng nhất trong báo cáo cuối: **mình vs HustVA**, và **model fine-tune vs model gốc**.

## 5. Ba giai đoạn

### Giai đoạn 1 (tuần 1–3): bản chạy đầu tiên bằng model gốc

Mục tiêu: hỏi trên web, model gốc (chưa fine-tune) chạy bằng Ollama trả lời thật có nguồn cho **một** chủ đề (quy chế đào tạo). Có điểm eval đầu tiên làm mốc.

| Người | Việc | Task |
| --- | --- | --- |
| TV2 | Lập danh sách nguồn → tải, làm sạch, cắt quy chế → đưa lên Supabase | [T1](13-data.md#t1--bảng-nguồn-tuần-1), [T4](13-data.md#t4--quy-chế-đào-tạo-lên-supabase-tuần-23) |
| Khiêm | Chọn model gốc, đo tốc độ trên Mac. Nối AI với Supabase, đo tìm đúng bao nhiêu %, chạy thật, chỉnh prompt. Thử Colab → Ollama với dữ liệu đồ chơi | [tuần 1](14-finetune.md#tuần-1--chọn-model-và-máy-chạy), [T5](12-ai-rag.md#t5--nối-supabase-và-đo-recallk-tuần-23), [T6](12-ai-rag.md#t6--chạy-thật-bằng-model-gốc-tuần-3), [bước 0](14-finetune.md#t14-bước-0--đi-thử-hết-đường-với-model-đồ-chơi-tuần-3) |
| TV3 | Viết bộ đề 100 câu + đáp án đúng; cả nhóm hỏi HustVA (mỗi người 25 câu) → chạy eval lần đầu | [T2](15-eval.md#t2--bộ-đề-v1-100-câu-tuần-12), [T8](15-eval.md#t8--chạy-eval-lần-đầu-tuần-3) |
| TV4 | Tạo Supabase → hoàn thiện UI → backend chạy trên Mac cùng Ollama, cả nhóm dùng qua Wi-Fi | [T3](11-backend.md#t3--làm-quen-và-tạo-supabase-tuần-1), [T7a](10-ui.md#t7a--đủ-trạng-thái-và-hiển-thị-tuần-23), [T7b](11-backend.md#t7b--nối-thật-và-chạy-chung-trên-máy-mac-tuần-3) |

### Giai đoạn 2 (tuần 4–5): đủ dữ liệu, sinh dữ liệu train, train lần đầu

Mục tiêu: đủ mọi chủ đề; có dataset ~1.000 mẫu; có model fine-tune đầu tiên.

| Người | Việc | Task |
| --- | --- | --- |
| TV2 | Thêm các nguồn còn lại, kiểm bảng số liệu, script cập nhật tự động. Cho agent làm vài lô dữ liệu train | [T9](13-data.md#t9--đủ-nguồn-và-cập-nhật-tự-động-tuần-45), [T13](14-finetune.md#t13--sinh-dataset-sft-tuần-45) |
| Khiêm | Chốt prompt. Chia lô và gom dữ liệu train, kiểm tay. Tìm kiếm tốt hơn (rerank, viết lại câu hỏi). Train LoRA lần đầu (cuối tuần 5) | [T13](14-finetune.md#t13--sinh-dataset-sft-tuần-45), [T10](12-ai-rag.md#t10--nâng-chất-lượng-truy-xuất-tuần-45), [T14](14-finetune.md#t14--train-lora-và-so-sánh-với-model-gốc-tuần-56) |
| TV3 | Kiểm giám khảo agent có chấm giống người không, mở rộng bộ đề lên 200 câu, phân loại câu sai. Cho agent làm vài lô dữ liệu train | [T11](15-eval.md#t11--tin-được-giám-khảo-và-bộ-đề-v2-tuần-45) |
| TV4 | Nút đánh giá Đúng/Sai, trang Giới thiệu, thống kê, giới hạn tải cho máy Mac. Cho agent làm vài lô dữ liệu train | [T12a](10-ui.md#t12a--feedback-và-giới-thiệu-tuần-4), [T12b](11-backend.md#t12b--thống-kê-cho-nhóm-tuần-4), [T19](11-backend.md#t19--giới-hạn-tải-cho-máy-mac-tuần-5) |

### Giai đoạn 3 (tuần 6–8): fine-tune tốt hơn model gốc, mở công khai, demo

Mục tiêu: model fine-tune có điểm cao hơn model gốc; bản công khai; báo cáo cuối.

| Người | Việc | Task |
| --- | --- | --- |
| TV2 | Sửa các văn bản mà eval chỉ ra là thiếu/lỗi, viết báo cáo phần Data | [T17](13-data.md#t17--báo-cáo-phần-data-tuần-8) |
| Khiêm | So sánh fine-tune vs model gốc, bổ sung dữ liệu và train lại nếu cần (v2). Guardrails. Chọn model cho demo | [T14](14-finetune.md#t14--train-lora-và-so-sánh-với-model-gốc-tuần-56), [T15](12-ai-rag.md#t15--guardrails-tuần-6) |
| TV3 | Chạy eval cho từng model mới, cho 10–20 sinh viên dùng thử, tổng hợp số liệu cuối | [So sánh](15-eval.md#so-sánh-model-gốc-và-model-fine-tune-tuần-56-theo-yêu-cầu-của-khiêm), [T16b](15-eval.md#t16b--thử-với-người-dùng-thật-tuần-7), [T17](15-eval.md#t17--số-liệu-tổng-tuần-8) |
| TV4 | Mở công khai qua Cloudflare Tunnel, kịch bản demo | [T16a](11-backend.md#t16a--mở-công-khai-tuần-7), [T18](10-ui.md#t18--kịch-bản-demo-tuần-8) |

## 6. Checkpoint (họp cuối tuần)

| Cuối tuần | Phải đạt | Chưa đạt thì |
| --- | --- | --- |
| 1 | Ai cũng chạy được bản mock. Có 100 câu hỏi + đáp án HustVA. Có ≥ 10 nguồn. Supabase có bảng. Đã chốt model gốc chạy được trên Mac. | Dời việc tải dữ liệu sang giữa tuần 2, ưu tiên bộ đề |
| 3 | Hỏi trên web ra câu trả lời thật có nguồn (quy chế) bằng model gốc. Có báo cáo eval đầu tiên. Đã đi thử hết Colab → Ollama. | Không thêm nguồn mới; cả nhóm sửa phần tìm kiếm |
| 5 | Đủ nguồn. Có dataset ~1.000 mẫu đã kiểm tay. Có model fine-tune đầu tiên chạy trên Ollama. | Tuần 6 cả nhóm dồn sức làm lô dữ liệu còn thiếu |
| 7 | Model fine-tune hơn model gốc trên bộ đề. Điểm ≥ HustVA về độ đúng và trích nguồn. Bản công khai. | Demo bằng bản tốt nhất đang có, ghi rõ kết quả trong báo cáo |

## 7. Ai đang chờ ai

| Người chờ | Chờ cái gì | Từ ai | Hạn |
| --- | --- | --- | --- |
| TV2 | Supabase đã tạo bảng + thông tin kết nối | TV4 | cuối tuần 1 |
| TV3 | Danh sách link văn bản (để ghi nguồn cho đáp án đúng) | TV2 | cuối tuần 1 |
| Khiêm | Bộ đề có ghi nguồn đúng dạng (để đo tìm kiếm) | TV3 | cuối tuần 2 |
| Khiêm | Quy chế đã lên Supabase | TV2 | giữa tuần 3 |
| TV3 | Chatbot chạy thật trên Mac để chấm | Khiêm + TV4 | cuối tuần 3 |
| Khiêm | File chunk đủ nguồn (để sinh dữ liệu train) | TV2 | đầu tuần 4 |
| Cả nhóm | Lô dữ liệu train được chia | Khiêm | tuần 4 |
| Khiêm | Các lô đã làm xong | Cả nhóm | giữa tuần 5 |

## 8. Thế nào là "xong" một task

- Chạy được trên máy người khác, không chỉ máy mình.
- Đạt mục "Kiểm tra" của task trong file hướng dẫn.
- Đã merge vào `main` qua PR có người review.
- Task của Data, AI, Fine-tune: PR có điểm eval trước/sau.

## 9. Cần chốt trong tuần 1

- Deadline thật? (kế hoạch giả định 8 tuần)
- Máy Mac nào chạy model và backend? Bao nhiêu RAM? (16 GB → model 3B; 24 GB trở lên → 7B). Máy đó phải bật khi chạy eval, khi mở công khai và khi demo.
- Tài khoản Colab Pro của ai, lưu checkpoint ở Drive nào?
- Điều khoản của AI agent mà nhóm dùng có cho dùng output để train model khác không? Hỏi giảng viên trước khi sinh dữ liệu train ([14-finetune.md, T13](14-finetune.md#t13--sinh-dataset-sft-tuần-45)).
- Ai giữ key Supabase `service_role`? (đề xuất: TV4, gửi riêng từng người)
