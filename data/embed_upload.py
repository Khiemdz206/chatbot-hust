"""Bước 4: tạo embedding cho từng chunk và đưa lên Supabase.

    python embed_upload.py

Cần trong .env: SUPABASE_URL, SUPABASE_SERVICE_KEY, EMBED_MODEL (mặc định BAAI/bge-m3).
Lần đầu sẽ tải model embedding (~2GB). Máy không có GPU vẫn chạy được, chỉ chậm hơn;
có thể chạy file này trên Colab rồi đẩy lên Supabase từ đó.

Văn bản đã có trên Supabase mà content_hash không đổi thì bỏ qua.
"""
import json
import os
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from supabase import create_client

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")


def main() -> None:
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    model = SentenceTransformer(os.getenv("EMBED_MODEL", "BAAI/bge-m3"))

    docs = defaultdict(list)
    with open(HERE / "chunks" / "chunks.jsonl", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            docs[row["url"]].append(row)

    for url, rows in docs.items():
        first = rows[0]
        existing = sb.table("documents").select("id, content_hash").eq("url", url).execute().data
        if existing and existing[0]["content_hash"] == first["content_hash"]:
            print(f"không đổi, bỏ qua: {first['title']}")
            continue

        doc = sb.table("documents").upsert({
            "title": first["title"], "url": url, "doc_type": first["doc_type"], "topic": first["topic"],
            "effective_date": first["effective_date"], "applies_to": first["applies_to"],
            "content_hash": first["content_hash"], "is_active": True,
        }, on_conflict="url").execute().data[0]

        sb.table("chunks").delete().eq("document_id", doc["id"]).execute()

        # Đưa section vào nội dung được embed để tìm "Điều 12" cũng ra
        texts = [f"{r['title']}. {r['section'] or ''}\n{r['content']}" for r in rows]
        vectors = model.encode(texts, normalize_embeddings=True, batch_size=16, show_progress_bar=True)

        sb.table("chunks").insert([
            {"document_id": doc["id"], "chunk_index": r["chunk_index"], "section": r["section"],
             "content": r["content"], "embedding": v.tolist()}
            for r, v in zip(rows, vectors)
        ]).execute()
        print(f"đã đưa lên: {first['title']} ({len(rows)} chunk)")


if __name__ == "__main__":
    main()
