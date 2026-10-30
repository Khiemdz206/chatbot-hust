"""Bước 1 của eval: hỏi hệ thống của nhóm toàn bộ câu trong bộ đề.

    python run_eval.py --golden golden/golden_v1.jsonl --api http://localhost:8000

Kết quả: results/<thời gian>_<commit>.jsonl, mỗi dòng gồm câu hỏi, đáp án chuẩn,
đáp án HustVA (lấy từ bộ đề) và đáp án của hệ thống mình.
Backend phải đang chạy. Đặt MIN_SECONDS_BETWEEN_QUESTIONS=0 trong .env khi chạy eval.
"""
import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

import httpx

HERE = Path(__file__).parent


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "nogit"


def main(golden: Path, api: str, limit: int | None) -> Path:
    items = [json.loads(l) for l in open(golden, encoding="utf-8") if l.strip()]
    if limit:
        items = items[:limit]
    out = HERE / "results" / f"{datetime.now():%Y%m%d-%H%M}_{git_commit()}.jsonl"
    out.parent.mkdir(exist_ok=True)

    with httpx.Client(timeout=120) as client, open(out, "w", encoding="utf-8") as f:
        for i, it in enumerate(items, 1):
            t0 = time.time()
            try:
                r = client.post(f"{api}/api/chat", params={"stream": "false"},
                                json={"message": it["question"], "session_id": "eval"})
                r.raise_for_status()
                res = r.json()
            except Exception as e:
                res = {"answer": "", "sources": [], "refused": None, "error": str(e)}
            f.write(json.dumps({**it, "system_answer": res.get("answer"), "system_sources": res.get("sources"),
                                "system_refused": res.get("refused"), "error": res.get("error"),
                                "latency_ms": int((time.time() - t0) * 1000)}, ensure_ascii=False) + "\n")
            print(f"[{i}/{len(items)}] {it['id']} {'LỖI' if res.get('error') else 'ok'}")
    print(f"Đã lưu: {out}\nTiếp theo: python judge.py {out}")
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--golden", type=Path, default=HERE / "golden" / "golden_v1.jsonl")
    p.add_argument("--api", default="http://localhost:8000")
    p.add_argument("--limit", type=int)
    a = p.parse_args()
    main(a.golden, a.api, a.limit)
