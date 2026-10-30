"""Bước 2 của eval: hai "giám khảo" LLM chấm câu trả lời của hệ thống mình và của HustVA.

    python judge.py results/20261110-2130_ab12cd3.jsonl

- Giám khảo không biết câu trả lời nào là của ai (gọi là "Câu trả lời A/B" ngẫu nhiên).
- Mỗi câu được chấm bởi JUDGE1 và JUDGE2 (nên là 2 model khác hãng).
  Hai giám khảo lệch nhau -> đánh dấu "can_cham_tay" để người chấm lại.
- Kết quả: <file>.judged.jsonl + <file>.report.md

Cần trong .env: JUDGE1_PROVIDER/JUDGE1_MODEL và JUDGE2_PROVIDER/JUDGE2_MODEL.
"""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.llm import chat, parse_json  # noqa: E402

RUBRIC = """Bạn là giám khảo chấm chatbot hỏi đáp học vụ đại học. Chấm từng câu trả lời độc lập theo rubric:
- correct: 2 = đúng và đủ ý so với đáp án chuẩn; 1 = đúng một phần hoặc thiếu ý quan trọng; 0 = sai hoặc không trả lời.
  Với câu NGOÀI PHẠM VI: 2 nếu từ chối lịch sự, 0 nếu cố trả lời.
- hallucination: true nếu có khẳng định cụ thể (số, mốc thời gian, điều kiện) không có trong đáp án chuẩn và có vẻ bịa.
- cites_source: true nếu câu trả lời có chỉ ra nguồn (số trích dẫn, tên văn bản hoặc link).
Chỉ trả về JSON:
{"A": {"correct": 0|1|2, "hallucination": bool, "cites_source": bool, "note": "..."},
 "B": {"correct": 0|1|2, "hallucination": bool, "cites_source": bool, "note": "..."}}"""


def judge_one(judge: str, item: dict, a: str, b: str) -> dict:
    user = (f"Câu hỏi: {item['question']}\n"
            f"Trong phạm vi học vụ: {'có' if item.get('in_scope', True) else 'KHÔNG'}\n"
            f"Đáp án chuẩn: {item['reference_answer']}\nNguồn chuẩn: {item.get('reference_source')}\n\n"
            f"Câu trả lời A:\n{a}\n\nCâu trả lời B:\n{b}")
    return parse_json(chat(judge, RUBRIC, user, max_tokens=800, temperature=0))


def main(path: Path) -> None:
    items = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    judged = []
    for it in items:
        ours = it.get("system_answer") or ""
        if it.get("system_sources"):
            ours += "\nNguồn: " + "; ".join(s["title"] for s in it["system_sources"])
        theirs = it.get("hustva_answer") or ""
        flip = random.random() < 0.5
        a, b = (theirs, ours) if flip else (ours, theirs)

        scores = {}
        for j in ("judge1", "judge2"):
            try:
                s = judge_one(j, it, a, b)
                scores[j] = {"ours": s["B" if flip else "A"], "hustva": s["A" if flip else "B"]}
            except Exception as e:
                scores[j] = {"error": str(e)}

        ok = [s for s in scores.values() if "error" not in s]
        disagree = len(ok) == 2 and (ok[0]["ours"]["correct"] != ok[1]["ours"]["correct"]
                                     or ok[0]["hustva"]["correct"] != ok[1]["hustva"]["correct"])
        judged.append({**it, "scores": scores, "can_cham_tay": disagree or len(ok) < 2})
        print(f"{it['id']}: {'CẦN CHẤM TAY' if judged[-1]['can_cham_tay'] else 'ok'}")

    out = path.with_suffix(".judged.jsonl")
    out.write_text("".join(json.dumps(j, ensure_ascii=False) + "\n" for j in judged), encoding="utf-8")
    write_report(judged, path.with_suffix(".report.md"))


def avg(xs):
    return sum(xs) / len(xs) if xs else 0.0


def write_report(judged: list[dict], out: Path) -> None:
    by_topic = defaultdict(lambda: {"ours": [], "hustva": []})
    tot = {"ours": defaultdict(list), "hustva": defaultdict(list)}
    for j in judged:
        ok = [s for s in j["scores"].values() if "error" not in s]
        for who in ("ours", "hustva"):
            for s in ok:
                tot[who]["correct"].append(s[who]["correct"] / 2)
                tot[who]["halluc"].append(1 if s[who]["hallucination"] else 0)
                tot[who]["cite"].append(1 if s[who]["cites_source"] else 0)
                by_topic[j.get("topic", "khac")][who].append(s[who]["correct"] / 2)

    lines = ["# Báo cáo eval", "", f"Số câu: {len(judged)}. Cần chấm tay: {sum(j['can_cham_tay'] for j in judged)}.", "",
             "| Chỉ số | Hệ thống mình | HustVA |", "| --- | --- | --- |"]
    for key, name in (("correct", "Độ chính xác"), ("cite", "Có trích nguồn"), ("halluc", "Có bịa")):
        lines.append(f"| {name} | {avg(tot['ours'][key]):.0%} | {avg(tot['hustva'][key]):.0%} |")
    lines += ["", "## Theo chủ đề", "", "| Chủ đề | Mình | HustVA |", "| --- | --- | --- |"]
    for t, v in sorted(by_topic.items()):
        lines.append(f"| {t} | {avg(v['ours']):.0%} | {avg(v['hustva']):.0%} |")
    lines += ["", "## Câu hệ thống mình sai (correct = 0 ở cả hai giám khảo)", ""]
    for j in judged:
        ok = [s for s in j["scores"].values() if "error" not in s]
        if ok and all(s["ours"]["correct"] == 0 for s in ok):
            lines.append(f"- **{j['id']}** {j['question']}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Báo cáo: {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
