"""Bước 1: tải từng nguồn trong sources.yaml về data/raw/.

    python crawl.py              # tải những nguồn chưa có
    python crawl.py --force      # tải lại tất cả

Kết quả: data/raw/<id>.html|pdf  +  data/raw/<id>.meta.json
Lịch sự với máy chủ của trường: đọc robots.txt, chờ giữa các lần tải.
"""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlparse

import httpx
import yaml

HERE = Path(__file__).parent
RAW = HERE / "raw"
UA = "ChatbotHUST-StudentProject/0.1 (do an mon hoc)"
DELAY_SECONDS = 2.0

_robots: dict[str, robotparser.RobotFileParser] = {}


def allowed(url: str) -> bool:
    host = urlparse(url)
    base = f"{host.scheme}://{host.netloc}"
    if base not in _robots:
        rp = robotparser.RobotFileParser(base + "/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None
        _robots[base] = rp
    rp = _robots[base]
    return True if rp is None else rp.can_fetch(UA, url)


def main(force: bool) -> None:
    RAW.mkdir(exist_ok=True)
    sources = yaml.safe_load((HERE / "sources.yaml").read_text(encoding="utf-8"))["sources"]
    with httpx.Client(headers={"User-Agent": UA}, timeout=30, follow_redirects=True) as client:
        for src in sources:
            out = RAW / f"{src['id']}.{src['type']}"
            if out.exists() and not force:
                print(f"bỏ qua (đã có): {src['id']}")
                continue
            if not allowed(src["url"]):
                print(f"robots.txt không cho phép: {src['url']}")
                continue
            try:
                r = client.get(src["url"])
                r.raise_for_status()
            except Exception as e:
                print(f"LỖI {src['id']}: {e}")
                continue
            out.write_bytes(r.content)
            meta = {**src, "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "content_hash": hashlib.sha256(r.content).hexdigest()}
            (RAW / f"{src['id']}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"đã tải: {src['id']} ({len(r.content) // 1024} KB)")
            time.sleep(DELAY_SECONDS)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    main(p.parse_args().force)
