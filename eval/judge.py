"""Bước 2 của eval: chấm câu trả lời của hệ thống mình và của HustVA.

Giám khảo là AI agent của người làm Eval, không gọi API. Script chuẩn bị đề,
chia lô, kiểm tra kết quả agent ghi ra và viết báo cáo. Cách làm từng bước:
docs/15-eval.md mục 4.

    python judge.py prepare results/<run>.jsonl
        -> results/<run>.judge_tasks.jsonl  (đề cho agent, A/B đảo ngẫu nhiên)
           results/<run>.judge_key.json     (A/B nào là của ai; agent KHÔNG được mở)

    python judge.py status results/<run>.jsonl [--size 25] [--paste]
        Đếm số câu đã chấm, báo dòng sai định dạng, in sẵn lời nhắn giao lô tiếp theo cho agent.
        --paste: in cả rubric và nội dung lô để dán vào AI chỉ chat được (không đọc/ghi file).

    python judge.py report results/<run>.jsonl
        -> results/<run>.judged.jsonl + results/<run>.report.md

Câu agent đánh dấu unsure, hoặc chưa được chấm -> "can_cham_tay" để người chấm lại.
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
RUBRIC = HERE / "RUBRIC.md"


def paths(results: Path) -> dict[str, Path]:
    stem = results.with_suffix("")
    return {name: Path(f"{stem}.{name}") for name in
            ("judge_tasks.jsonl", "judge_key.json", "judge_scores.jsonl", "judged.jsonl", "report.md")}


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def check_score(row) -> str | None:
    """Trả về lý do sai định dạng, hoặc None nếu dòng hợp lệ."""
    if not isinstance(row, dict) or "id" not in row:
        return "thiếu id"
    for side in ("A", "B"):
        s = row.get(side)
        if not isinstance(s, dict):
            return f"thiếu {side}"
        if s.get("correct") not in (0, 1, 2):
            return f"{side}.correct phải là 0, 1 hoặc 2"
        for f in ("hallucination", "cites_source"):
            if not isinstance(s.get(f), bool):
                return f"{side}.{f} phải là true/false"
    return None


def load_scores(p: dict[str, Path], task_ids: set[str]) -> tuple[dict[str, dict], list[str]]:
    """Đọc file điểm agent ghi. Dòng sau ghi đè dòng trước cùng id. Trả về (điểm hợp lệ, danh sách lỗi)."""
    scores, errors = {}, []
    if not p["judge_scores.jsonl"].exists():
        return scores, errors
    for i, line in enumerate(open(p["judge_scores.jsonl"], encoding="utf-8"), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"dòng {i}: không phải JSON")
            continue
        reason = check_score(row)
        if not reason and row["id"] not in task_ids:
            reason = f"id {row['id']} không có trong đề"
        if reason:
            errors.append(f"dòng {i}: {reason}")
        else:
            scores[row["id"]] = row
    return scores, errors


def prepare(results: Path, seed: int) -> None:
    random.seed(seed)
    p = paths(results)
    if p["judge_scores.jsonl"].exists():
        raise SystemExit(f"Đã có {p['judge_scores.jsonl'].name}: chạy prepare lại sẽ đảo A/B khác và làm sai điểm cũ. "
                         "Muốn chấm lại từ đầu thì xoá file đó trước.")
    tasks, key = [], {}
    for it in load(results):
        ours = it.get("system_answer") or ""
        if it.get("system_sources"):
            ours += "\nNguồn: " + "; ".join(s["title"] for s in it["system_sources"])
        theirs = it.get("hustva_answer") or ""
        flip = random.random() < 0.5
        a, b = (theirs, ours) if flip else (ours, theirs)
        key[it["id"]] = {"ours": "B" if flip else "A", "hustva": "A" if flip else "B"}
        tasks.append({"id": it["id"], "question": it["question"], "in_scope": it.get("in_scope", True),
                      "reference_answer": it["reference_answer"], "reference_source": it.get("reference_source"),
                      "A": a, "B": b})
    p["judge_tasks.jsonl"].write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks), encoding="utf-8")
    p["judge_key.json"].write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(tasks)} câu -> {p['judge_tasks.jsonl']}")
    print(f"Tiếp theo: python judge.py status {results.as_posix()}")


def status(results: Path, size: int, paste: bool) -> None:
    p = paths(results)
    tasks = load(p["judge_tasks.jsonl"])
    scores, errors = load_scores(p, {t["id"] for t in tasks})
    missing = [t for t in tasks if t["id"] not in scores]
    print(f"Đã chấm hợp lệ: {len(scores)}/{len(tasks)} câu.")
    if errors:
        print(f"{len(errors)} dòng sai định dạng (bị bỏ qua, các câu đó coi như chưa chấm):")
        for e in errors[:10]:
            print("  -", e)
    if not missing:
        print(f"Đã chấm đủ. Chạy: python judge.py report {results.as_posix()}")
        return

    batch = missing[:size]
    ids = ", ".join(t["id"] for t in batch)
    # đường dẫn tính từ thư mục gốc repo, nơi agent thường đứng
    tasks_path, scores_path = (p[n].resolve().relative_to(HERE.parent.resolve()).as_posix()
                               for n in ("judge_tasks.jsonl", "judge_scores.jsonl"))
    print(f"\nLô tiếp theo: {len(batch)} câu. Còn lại sau lô này: {len(missing) - len(batch)}.")
    print("=" * 70)
    if not paste:
        print(f"Đọc file eval/RUBRIC.md và làm đúng theo đó. Chấm các câu có id sau trong file {tasks_path}:\n"
              f"{ids}\n"
              f"Ghi kết quả nối tiếp vào cuối file {scores_path} (tạo file nếu chưa có), "
              f"mỗi câu một dòng JSON đúng định dạng trong RUBRIC.md. Không mở file nào khác trong eval/results/.")
    else:
        rubric = RUBRIC.read_text(encoding="utf-8")
        print(rubric)
        print("\n## Các câu cần chấm\n\nChỉ trả về các dòng JSON kết quả, mỗi câu một dòng, không viết gì thêm.\n")
        for t in batch:
            print(json.dumps(t, ensure_ascii=False))
    print("=" * 70)
    if paste:
        print(f"Chép các dòng JSON AI trả về, dán vào CUỐI file {scores_path}, lưu lại, rồi chạy lại lệnh status.")
    else:
        print("Chép đoạn giữa hai đường kẻ, gửi cho agent. Agent làm xong thì chạy lại lệnh status.")


def report(results: Path) -> None:
    p = paths(results)
    key = json.loads(p["judge_key.json"].read_text(encoding="utf-8"))
    scores, errors = load_scores(p, set(key))
    if errors:
        print(f"CẢNH BÁO: {len(errors)} dòng sai định dạng bị bỏ qua (xem bằng lệnh status)")

    judged = []
    for it in load(results):
        s = scores.get(it["id"])
        if s:
            k = key[it["id"]]
            entry = {"ours": s[k["ours"]], "hustva": s[k["hustva"]]}
            judged.append({**it, "scores": entry, "can_cham_tay": bool(s.get("unsure"))})
        else:
            judged.append({**it, "scores": None, "can_cham_tay": True})
    p["judged.jsonl"].write_text("".join(json.dumps(j, ensure_ascii=False) + "\n" for j in judged), encoding="utf-8")
    write_report(judged, p["report.md"])
    missing = sum(1 for j in judged if j["scores"] is None)
    if missing:
        print(f"CẢNH BÁO: {missing} câu chưa được chấm. Chạy lệnh status để giao tiếp cho agent.")


def avg(xs):
    return sum(xs) / len(xs) if xs else 0.0


def write_report(judged: list[dict], out: Path) -> None:
    by_topic = defaultdict(lambda: {"ours": [], "hustva": []})
    tot = {"ours": defaultdict(list), "hustva": defaultdict(list)}
    for j in judged:
        if not j["scores"]:
            continue
        for who in ("ours", "hustva"):
            s = j["scores"][who]
            tot[who]["correct"].append(s["correct"] / 2)
            tot[who]["halluc"].append(1 if s["hallucination"] else 0)
            tot[who]["cite"].append(1 if s["cites_source"] else 0)
            by_topic[j.get("topic", "khac")][who].append(s["correct"] / 2)

    lines = ["# Báo cáo eval", "",
             f"Số câu: {len(judged)}. Đã chấm: {sum(1 for j in judged if j['scores'])}. "
             f"Cần chấm tay: {sum(j['can_cham_tay'] for j in judged)}.", "",
             "| Chỉ số | Hệ thống mình | HustVA |", "| --- | --- | --- |"]
    for key, name in (("correct", "Độ chính xác"), ("cite", "Có trích nguồn"), ("halluc", "Có bịa")):
        lines.append(f"| {name} | {avg(tot['ours'][key]):.0%} | {avg(tot['hustva'][key]):.0%} |")
    lines += ["", "## Theo chủ đề", "", "| Chủ đề | Mình | HustVA |", "| --- | --- | --- |"]
    for t, v in sorted(by_topic.items()):
        lines.append(f"| {t} | {avg(v['ours']):.0%} | {avg(v['hustva']):.0%} |")
    lines += ["", "## Câu hệ thống mình sai (correct = 0)", ""]
    for j in judged:
        if j["scores"] and j["scores"]["ours"]["correct"] == 0:
            lines.append(f"- **{j['id']}** {j['question']} — {j['scores']['ours'].get('note', '')}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Báo cáo: {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["prepare", "status", "report"])
    ap.add_argument("results", type=Path)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--size", type=int, default=25, help="số câu mỗi lô (lệnh status)")
    ap.add_argument("--paste", action="store_true", help="in cả rubric và đề để dán vào AI chỉ chat được")
    a = ap.parse_args()
    if a.step == "prepare":
        prepare(a.results, a.seed)
    elif a.step == "status":
        status(a.results, a.size, a.paste)
    else:
        report(a.results)
