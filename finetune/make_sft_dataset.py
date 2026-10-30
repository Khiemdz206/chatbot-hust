"""Sinh dữ liệu fine-tune (SFT). "Teacher" là AI agent của các thành viên, không gọi API.

Script chia việc thành từng lô nhỏ để agent của mỗi thành viên làm một phần,
rồi gom lại. Hướng dẫn cho agent: finetune/TEACHER.md.

    python make_sft_dataset.py questions --n 200
        Lấy ngẫu nhiên n chunk từ data/chunks/chunks.jsonl
        -> datasets/q_tasks/batch_XXX.jsonl          (mỗi lô 20 chunk)
        Agent viết câu hỏi -> datasets/q_tasks/batch_XXX.out.jsonl

    python make_sft_dataset.py contexts
        Đọc mọi q_tasks/*.out.jsonl, bỏ câu giống bộ eval, dựng ngữ cảnh như lúc chạy thật
        (chunk đúng + 3 chunk nhiễu, xáo trộn; ~15% bỏ chunk đúng để dạy nói "chưa tìm thấy")
        bằng ĐÚNG build_messages() của backend
        -> datasets/a_tasks/batch_XXX.jsonl          (mỗi lô 20 câu)
        Agent viết câu trả lời -> datasets/a_tasks/batch_XXX.out.jsonl

    python make_sft_dataset.py build
        Gom câu trả lời, lọc, ghi datasets/sft.jsonl, in thống kê.
        Mỗi dòng {"messages": [system, user, assistant], "meta": {...}}: Unsloth/TRL đọc thẳng được.
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from app.rag.prompts import SYSTEM_PROMPT, build_messages  # noqa: E402
from app.rag.retriever import Chunk  # noqa: E402

DATASETS = Path(__file__).parent / "datasets"
Q_DIR, A_DIR = DATASETS / "q_tasks", DATASETS / "a_tasks"
BATCH = 20
UNANSWERABLE_RATE = 0.15
NOT_FOUND = "chưa tìm thấy"   # cụm bắt buộc trong câu trả lời khi tài liệu không đủ (quy tắc 3 của SYSTEM_PROMPT)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def write_batches(folder: Path, rows: list[dict]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("batch_*.jsonl"):
        if not old.name.endswith(".out.jsonl"):
            old.unlink()
    for i in range(0, len(rows), BATCH):
        out = folder / f"batch_{i // BATCH + 1:03d}.jsonl"
        out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows[i:i + BATCH]), encoding="utf-8")
    print(f"{len(rows)} việc -> {folder} ({(len(rows) + BATCH - 1) // BATCH} lô)")


def read_outputs(folder: Path) -> list[dict]:
    rows = []
    for p in sorted(folder.glob("batch_*.out.jsonl")):
        rows += load_jsonl(p)
    return rows


def load_chunks() -> dict[str, Chunk]:
    rows = load_jsonl(REPO / "data" / "chunks" / "chunks.jsonl")
    return {f"{r['source_id']}#{r['chunk_index']}": Chunk(
        id=f"{r['source_id']}#{r['chunk_index']}", title=r["title"], content=r["content"],
        section=r["section"], url=r["url"], effective_date=r["effective_date"]) for r in rows}


def norm(s: str) -> str:
    return " ".join(re.findall(r"\w+", s.lower()))


def load_eval_questions() -> list[set[str]]:
    qs = []
    for p in (REPO / "eval" / "golden").glob("*.jsonl"):
        qs += [set(norm(r["question"]).split()) for r in load_jsonl(p)]
    return qs


def too_similar(q: str, eval_qs: list[set[str]]) -> bool:
    a = set(norm(q).split())
    return any(a and b and len(a & b) / len(a | b) > 0.7 for b in eval_qs)


# ------------------------------------------------------------ các bước

def step_questions(n: int) -> None:
    chunks = list(load_chunks().values())
    picked = random.sample(chunks, min(n, len(chunks)))
    write_batches(Q_DIR, [{"chunk_id": c.id, "title": c.title, "section": c.section, "content": c.content}
                          for c in picked])


def step_contexts() -> None:
    chunks = load_chunks()
    eval_qs = load_eval_questions()
    tasks, dropped = [], 0
    for row in read_outputs(Q_DIR):
        target = chunks.get(row["chunk_id"])
        if not target:
            continue
        for q in row["questions"]:
            if too_similar(q, eval_qs):
                dropped += 1
                continue
            answerable = random.random() > UNANSWERABLE_RATE
            others = [c for cid, c in chunks.items() if cid != target.id]
            context = random.sample(others, min(3, len(others)))
            if answerable:
                context.append(target)
            random.shuffle(context)
            user = build_messages(q, context)[-1]["content"]
            tasks.append({"task_id": f"{target.id}|{len(tasks)}", "answerable": answerable, "user": user})
    print(f"bỏ {dropped} câu giống bộ eval")
    write_batches(A_DIR, tasks)


def step_build() -> None:
    tasks = {}
    for p in sorted(A_DIR.glob("batch_*.jsonl")):
        if not p.name.endswith(".out.jsonl"):
            tasks.update({t["task_id"]: t for t in load_jsonl(p)})
    kept, reasons, lengths = [], {"thiếu [n]": 0, "lẽ ra phải nói chưa tìm thấy": 0, "không có task": 0}, []
    for row in read_outputs(A_DIR):
        t = tasks.get(row["task_id"])
        if not t:
            reasons["không có task"] += 1
            continue
        answer = row["answer"].strip()
        has_cite = bool(re.search(r"\[\d+\]", answer))
        if t["answerable"] and not has_cite:
            reasons["thiếu [n]"] += 1
            continue
        if not t["answerable"] and (has_cite or NOT_FOUND not in answer.lower()):
            reasons["lẽ ra phải nói chưa tìm thấy"] += 1
            continue
        kept.append({"messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                  {"role": "user", "content": t["user"]},
                                  {"role": "assistant", "content": answer}],
                     "meta": {"task_id": t["task_id"], "answerable": t["answerable"]}})
        lengths.append(len(answer.split()))
    out = DATASETS / "sft.jsonl"
    out.write_text("".join(json.dumps(k, ensure_ascii=False) + "\n" for k in kept), encoding="utf-8")
    unans = sum(1 for k in kept if not k["meta"]["answerable"])
    print(f"Giữ {len(kept)} mẫu -> {out}")
    print(f"Không trả lời được: {unans} ({unans / max(1, len(kept)):.0%}). Độ dài TB: {sum(lengths) / max(1, len(lengths)):.0f} từ")
    print("Bỏ:", ", ".join(f"{k} {v}" for k, v in reasons.items()))
    print("Nhớ kiểm tay ngẫu nhiên ~5% trước khi train.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["questions", "contexts", "build"])
    ap.add_argument("--n", type=int, default=200, help="số chunk dùng để sinh câu hỏi (bước questions)")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    random.seed(a.seed)
    {"questions": lambda: step_questions(a.n), "contexts": step_contexts, "build": step_build}[a.step]()
