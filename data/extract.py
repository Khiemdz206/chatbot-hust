"""Bước 2: trích văn bản sạch từ data/raw/ sang data/clean/<id>.md

    python extract.py

- HTML: bỏ menu, header, footer, script; giữ tiêu đề, đoạn văn, bảng.
- PDF có lớp chữ: trích bằng pypdf.
- PDF scan (gần như không có chữ): in cảnh báo. Xử lý tay theo docs/13-data.md
  (nhờ model mạnh đọc PDF, kiểm lại rồi lưu kết quả vào data/clean/<id>.md).
"""
import json
import re
import shutil
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

HERE = Path(__file__).parent
RAW, CLEAN = HERE / "raw", HERE / "clean"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)       # thống nhất cách gõ dấu tiếng Việt
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def from_html(path: Path) -> str:
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        tag.decompose()
    # TODO: khi biết cấu trúc trang CTT, chọn đúng khung nội dung chính, vd. soup.select_one(".article-content")
    main = soup.find("article") or soup.find("main") or soup.body or soup
    lines = []
    for el in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "tr"]):
        if el.name == "tr":
            cells = [c.get_text(" ", strip=True) for c in el.find_all(["td", "th"])]
            if any(cells):
                lines.append("| " + " | ".join(cells) + " |")
        else:
            t = el.get_text(" ", strip=True)
            if t:
                prefix = "#" * int(el.name[1]) + " " if el.name.startswith("h") else ("- " if el.name == "li" else "")
                lines.append(prefix + t)
    return "\n\n".join(lines)


def from_pdf(path: Path) -> tuple[str, bool]:
    reader = PdfReader(str(path))
    pages = [p.extract_text() or "" for p in reader.pages]
    text = "\n\n".join(pages)
    looks_scanned = len(text.strip()) < 200 * max(1, len(pages)) * 0.3
    return text, looks_scanned


def main() -> None:
    CLEAN.mkdir(exist_ok=True)
    for meta_path in sorted(RAW.glob("*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        raw = RAW / f"{meta['id']}.{meta['type']}"
        out = CLEAN / f"{meta['id']}.md"
        if meta["type"] == "html":
            text = from_html(raw)
        else:
            text, scanned = from_pdf(raw)
            if scanned:
                print(f"CẦN XỬ LÝ TAY (PDF scan): {meta['id']} – xem docs/13-data.md")
                continue
        out.write_text(normalize(text), encoding="utf-8")
        shutil.copy(meta_path, CLEAN / meta_path.name)
        print(f"đã làm sạch: {meta['id']} ({len(text)} ký tự)")


if __name__ == "__main__":
    main()
