"""Bước 3: chia văn bản sạch thành các đoạn (chunk) -> data/chunks/chunks.jsonl

    python chunk.py

Ưu tiên chia theo cấu trúc văn bản pháp quy: Chương -> Điều -> Khoản.
Mỗi chunk mang theo "section" (vd. "Chương II – Điều 12. Đăng ký học tập")
để khi đứng một mình vẫn hiểu được, và để trích dẫn chính xác.
Văn bản không có cấu trúc Điều (thông báo, tin tức) thì gom đoạn văn đến ~MAX_CHARS.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
CLEAN, OUT = HERE / "clean", HERE / "chunks"

MAX_CHARS = 2500   # ~600-800 token tiếng Việt; chỉnh sau khi chạy eval
MIN_CHARS = 200

RE_CHUONG = re.compile(r"^(?:#+\s*)?(CHƯƠNG|Chương)\s+([IVXLC\d]+)\.?\s*(.*)$")
RE_DIEU = re.compile(r"^(?:#+\s*)?(Điều)\s+(\d+)\.?\s*(.*)$")
RE_KHOAN = re.compile(r"^\d+\.\s")


def split_long(text: str, limit: int = MAX_CHARS) -> list[str]:
    """Cắt đoạn dài theo Khoản (dòng bắt đầu bằng '1.', '2.'...), không thì theo đoạn văn."""
    if len(text) <= limit:
        return [text]
    lines = text.split("\n")
    parts, cur = [], []
    for line in lines:
        if (RE_KHOAN.match(line) or not line.strip()) and sum(map(len, cur)) > limit * 0.6:
            parts.append("\n".join(cur).strip())
            cur = []
        cur.append(line)
    if cur:
        parts.append("\n".join(cur).strip())
    return [p for p in parts if p]


def chunk_structured(text: str) -> list[tuple[str, str]]:
    """Trả về [(section, content)] theo Chương/Điều."""
    out, chuong, dieu, buf = [], "", "", []

    def flush():
        body = "\n".join(buf).strip()
        if body:
            section = " – ".join(x for x in (chuong, dieu) if x)
            for part in split_long(body):
                out.append((section, part))

    for line in text.split("\n"):
        line_s = line.strip()
        if m := RE_CHUONG.match(line_s):
            flush(); buf = []
            chuong = f"Chương {m.group(2)}" + (f". {m.group(3)}" if m.group(3) else "")
            dieu = ""
        elif m := RE_DIEU.match(line_s):
            flush(); buf = []
            dieu = f"Điều {m.group(2)}" + (f". {m.group(3)}" if m.group(3) else "")
        else:
            buf.append(line)
    flush()
    return out


def chunk_plain(text: str) -> list[tuple[str, str]]:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    out, cur = [], ""
    for p in paras:
        if len(cur) + len(p) > MAX_CHARS and len(cur) >= MIN_CHARS:
            out.append(("", cur))
            cur = ""
        cur = (cur + "\n\n" + p).strip()
    if cur:
        out.append(("", cur))
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    total = 0
    with open(OUT / "chunks.jsonl", "w", encoding="utf-8") as f:
        for md in sorted(CLEAN.glob("*.md")):
            meta = json.loads((CLEAN / f"{md.stem}.meta.json").read_text(encoding="utf-8"))
            text = md.read_text(encoding="utf-8")
            has_dieu = sum(1 for line in text.split("\n") if RE_DIEU.match(line.strip())) >= 2
            pieces = chunk_structured(text) if has_dieu else chunk_plain(text)
            for i, (section, content) in enumerate(pieces):
                f.write(json.dumps({
                    "source_id": meta["id"], "title": meta["title"], "url": meta["url"],
                    "doc_type": meta.get("doc_type"), "topic": meta.get("topic"),
                    "effective_date": meta.get("effective_date"), "applies_to": meta.get("applies_to"),
                    "content_hash": meta.get("content_hash"),
                    "chunk_index": i, "section": section or None, "content": content,
                }, ensure_ascii=False) + "\n")
            total += len(pieces)
            print(f"{md.stem}: {len(pieces)} chunk ({'theo Điều' if has_dieu else 'theo đoạn'})")
    print(f"Tổng: {total} chunk -> {OUT / 'chunks.jsonl'}")


if __name__ == "__main__":
    main()
