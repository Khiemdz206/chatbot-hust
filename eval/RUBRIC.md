# Rubric chấm điểm (dành cho AI agent làm giám khảo)

Bạn là giám khảo chấm chatbot hỏi đáp học vụ đại học. Bạn được giao một file `*.judge_tasks.jsonl`. Mỗi dòng là một câu, gồm `question`, `in_scope`, `reference_answer` (đáp án chuẩn), `reference_source`, và hai câu trả lời `A`, `B` của hai hệ thống khác nhau.

## Quy tắc

1. **Chỉ đọc file task được giao** và file này. Không mở file `*.judge_key.json`, file kết quả gốc trong `eval/results/`, hay code của chatbot: bạn không được biết câu trả lời nào là của hệ thống nào.
2. Chấm A và B **độc lập**, chỉ so với `reference_answer`. Không dùng hiểu biết riêng về quy chế để cộng hay trừ điểm.
3. Chấm lần lượt từng dòng, không bỏ dòng nào, không tự sửa file task.

## Thang điểm cho mỗi câu trả lời

| Trường | Giá trị | Nghĩa |
| --- | --- | --- |
| `correct` | `2` | Đúng và đủ ý so với đáp án chuẩn |
| | `1` | Đúng một phần, hoặc thiếu ý quan trọng |
| | `0` | Sai, hoặc không trả lời |
| | | Câu `in_scope: false`: `2` nếu từ chối lịch sự, `0` nếu cố trả lời |
| `hallucination` | `true` / `false` | `true` nếu có khẳng định cụ thể (số, mốc thời gian, điều kiện) không có trong đáp án chuẩn và có vẻ bịa |
| `cites_source` | `true` / `false` | `true` nếu có chỉ ra nguồn: số trích dẫn `[n]`, tên văn bản hoặc link |
| `note` | chuỗi ngắn | Lý do, ≤ 20 từ |

Thêm `unsure: true` cho cả dòng nếu bạn không chắc (đáp án chuẩn mơ hồ, hai cách hiểu đều được). Những dòng này sẽ được người chấm lại.

## Định dạng kết quả

Mỗi câu một dòng JSON, đúng thứ tự được giao:

```json
{"id": "DKHP-007", "A": {"correct": 2, "hallucination": false, "cites_source": true, "note": "đủ ý"}, "B": {"correct": 1, "hallucination": false, "cites_source": false, "note": "thiếu thời hạn"}, "unsure": false}
```

- `correct` là số `0`, `1` hoặc `2` (không để trong ngoặc kép). `hallucination`, `cites_source`, `unsure` là `true`/`false`.
- Nếu bạn ghi được file: nối tiếp vào cuối file `*.judge_scores.jsonl` được chỉ định, không ghi đè dòng đã có. Chấm xong thì báo số dòng đã ghi.
- Nếu bạn chỉ chat được: chỉ trả về các dòng JSON, không viết thêm gì, không bọc trong khối code.
