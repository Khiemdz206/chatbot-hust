"""Sinh dữ liệu fine-tune (SFT) bằng model mạnh làm "teacher".

    python make_sft_dataset.py --n 300 --out datasets/sft.jsonl

Với mỗi chunk trong data/chunks/chunks.jsonl:
  1. Teacher sinh vài câu hỏi kiểu sinh viên.
  2. Dựng ngữ cảnh giống lúc chạy thật: chunk đúng + vài chunk gây nhiễu, xáo trộn.
     ~15% mẫu cố tình BỎ chunk đúng để model học cách nói "chưa tìm thấy".
  3. Teacher trả lời với ĐÚNG system prompt + build_messages() của backend.
  4. Lọc: mẫu trả lời được phải có trích dẫn [n]; bỏ câu trùng bộ eval.

Kết quả: mỗi dòng {"messages": [system, user, assistant]} – định dạng chat chuẩn,
Unsloth/TRL đọc thẳng được.

Cần trong .env: TEACHER_PROVIDER, TEACHER_MODEL (+ API key tương ứng).
LƯU Ý: đọc điều khoản của nhà cung cấp về việc dùng output để train model khác.
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))

from app.rag.prompts import SYSTEM_PROMPT, build_messages  # noqa: E402
from app.rag.retriever import Chunk  # noqa: E402
from common.llm import chat, parse_json  # noqa: E402

QUESTION_PROMPT = """Dưới đây là một đoạn văn bản học vụ của Đại học Bách khoa Hà Nội.
Viết {k} câu hỏi mà sinh viên có thể hỏi và đoạn văn bản này trả lời được.
Yêu cầu: văn phong tự nhiên như sinh viên nhắn tin (có thể viết tắt: đkhp, tc, CPA, GPA...),
đa dạng độ khó, không chép nguyên câu trong văn bản.
Chỉ trả về JSON: {{"questions": ["...", "..."]}}

<doan_van_ban>
{section}
{content}
</doan_van_ban>"""


def load_chunks() -> list[Chunk]:
    rows = [json.loads(l) for l in open(REPO / "data" / "chunks" / "chunks.jsonl", encoding="utf-8")]
    return [Chunk(id=f"{r['source_id']}#{r['chunk_index']}", title=r["title"], content=r["content"],
                  section=r["section"], url=r["url"], effective_date=r["effective_date"]) for r in rows]


def load_eval_questions() -> set[str]:
    qs = set()
    for p in (REPO / "eval" / "golden").glob("*.jsonl"):
        for line in open(p, encoding="utf-8"):
            if line.strip():
                qs.add(norm(json.loads(line)["question"]))
    return qs


def norm(s: str) -> str:
    return " ".join(re.findall(r"\w+", s.lower()))


def too_similar(q: str, eval_qs: set[str]) -> bool:
    a = set(norm(q).split())
    for e in eval_qs:
        b = set(e.split())
        if a and b and len(a & b) / len(a | b) > 0.7:
            return True
    return False


def main(n: int, per_chunk: int, out: Path, seed: int) -> None:
    random.seed(seed)
    chunks = load_chunks()
    eval_qs = load_eval_questions()
    out.parent.mkdir(parents=True, exist_ok=True)
    kept = dropped = 0

    with open(out, "a", encoding="utf-8") as f:
        for target in random.sample(chunks, min(n, len(chunks))):
            try:
                qs = parse_json(chat("teacher", "Bạn tạo dữ liệu huấn luyện.",
                                     QUESTION_PROMPT.format(k=per_chunk, section=target.section or "", content=target.content)))["questions"]
            except Exception as e:
                print(f"bỏ chunk {target.id}: {e}")
                continue

            for q in qs:
                if too_similar(q, eval_qs):
                    dropped += 1
                    continue
                answerable = random.random() > 0.15
                others = [c for c in chunks if c.id != target.id]
                context = random.sample(others, min(3, len(others)))
                if answerable:
                    context.append(target)
                random.shuffle(context)

                messages = build_messages(q, context)
                answer = chat("teacher", SYSTEM_PROMPT, messages[-1]["content"])

                has_cite = bool(re.search(r"\[\d+\]", answer))
                if answerable and not has_cite:
                    dropped += 1
                    continue

                f.write(json.dumps({
                    "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages,
                                 {"role": "assistant", "content": answer}],
                    "meta": {"target": target.id, "answerable": answerable},
                }, ensure_ascii=False) + "\n")
                kept += 1
            print(f"giữ {kept}, bỏ {dropped}")

    print(f"Xong. {kept} mẫu -> {out}. Nhớ kiểm tay ngẫu nhiên ~5% trước khi train.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=300, help="số chunk dùng để sinh")
    p.add_argument("--per-chunk", type=int, default=4)
    p.add_argument("--out", type=Path, default=Path(__file__).parent / "datasets" / "sft.jsonl")
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    main(a.n, a.per_chunk, a.out, a.seed)
