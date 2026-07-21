#!/usr/bin/env python3
"""Adaptively collect and triage Xianyu comparables through OpenCLI.

The output is evidence for a model or subagent, not a final personal-seller
classification. Use --fixture for offline tests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Iterable, Optional

from parse_utils import parse_price


PERSONAL = (
    "自用", "个人", "闲置", "购入", "买来", "用得少", "吃灰", "整套出",
)
MERCHANT = (
    "严选", "质保", "回收", "置换", "仓直发", "店铺", "一机一图",
    "七天无理由", "长期出售", "客服", "验货宝仓",
)
DEFAULT_EXCLUDE = (
    "求购", "租赁", "出租", "维修", "教程", "代拍", "回收价",
)


def parse_json_array(output: str) -> list[dict]:
    start = output.find("[")
    if start < 0:
        raise ValueError("OpenCLI output did not contain a JSON array")
    payload = json.loads(output[start:])
    if not isinstance(payload, list):
        raise ValueError("OpenCLI search output must be a JSON array")
    return [item for item in payload if isinstance(item, dict)]


def search_opencli(
    query: str,
    limit: int,
    min_price: Optional[float],
    max_price: Optional[float],
) -> list[dict]:
    cmd = [
        "opencli", "xianyu", "search", query, "--limit", str(limit),
        "-f", "json", "--window", "background",
        "--site-session", "persistent", "--keep-tab", "false",
    ]
    if min_price is not None:
        cmd.extend(["--min-price", str(min_price)])
    if max_price is not None:
        cmd.extend(["--max-price", str(max_price)])
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"search failed: {query}")
    try:
        return parse_json_array(proc.stdout)
    except (ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid search output for {query}: {exc}") from exc


def fixture_searcher(path: Path) -> Callable[[str, int, Optional[float], Optional[float]], list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    def run(query: str, limit: int, min_price: Optional[float], max_price: Optional[float]) -> list[dict]:
        if isinstance(payload, dict):
            rows = payload.get(query, [])
        elif isinstance(payload, list):
            rows = payload
        else:
            raise ValueError("fixture must be a list or a query-to-list mapping")
        result = []
        for item in rows:
            price = parse_price(item.get("price")) if isinstance(item, dict) else None
            if min_price is not None and price is not None and price < min_price:
                continue
            if max_price is not None and price is not None and price > max_price:
                continue
            if isinstance(item, dict):
                result.append(item)
        return result[:limit]

    return run


def deduplicate(items: Iterable[dict]) -> list[dict]:
    unique: dict[str, dict] = {}
    for item in items:
        item_id = str(item.get("item_id", "")).strip()
        if item_id:
            unique[item_id] = item
    return list(unique.values())


def triage(items: Iterable[dict], exclude_words: Iterable[str] = DEFAULT_EXCLUDE) -> list[dict]:
    rows = []
    exclusions = tuple(word for word in exclude_words if word)
    for item in deduplicate(items):
        title = str(item.get("title", ""))
        merchant = any(word in title for word in MERCHANT)
        excluded = any(word in title for word in exclusions)
        personal = any(word in title for word in PERSONAL) and not merchant and not excluded
        price = parse_price(item.get("price"))
        rows.append({
            **item,
            "parsed_price": price,
            "likely_personal": personal,
            "likely_merchant": merchant,
            "excluded_by_title": excluded,
            "candidate": not merchant and not excluded,
        })
    return rows


def median_candidate_price(rows: Iterable[dict]) -> Optional[float]:
    prices = [float(row["parsed_price"]) for row in rows if row.get("candidate") and row.get("parsed_price")]
    return statistics.median(prices) if prices else None


def relative_change(before: Optional[float], after: Optional[float]) -> Optional[float]:
    if before is None or after is None or before == 0:
        return None
    return abs(after - before) / before


def collect(
    queries: list[str],
    searcher: Callable[[str, int, Optional[float], Optional[float]], list[dict]],
    batch_limit: int = 50,
    max_raw: int = 200,
    min_candidates: int = 40,
    stability_threshold: float = 0.03,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    exclude_words: Iterable[str] = DEFAULT_EXCLUDE,
) -> dict:
    raw: list[dict] = []
    batches = []
    previous_median: Optional[float] = None
    stable = False
    stopped_reason = "queries_exhausted"

    for query in queries:
        remaining = max_raw - len(raw)
        if remaining <= 0:
            stopped_reason = "max_raw"
            break
        fetched = searcher(query, min(batch_limit, remaining), min_price, max_price)
        raw.extend(fetched[:remaining])
        rows = triage(raw, exclude_words)
        candidate_count = sum(bool(row["candidate"]) for row in rows)
        current_median = median_candidate_price(rows)
        change = relative_change(previous_median, current_median)
        batches.append({
            "query": query,
            "fetched": len(fetched[:remaining]),
            "raw_total": len(raw),
            "unique_total": len(rows),
            "candidate_total": candidate_count,
            "median_candidate_price": current_median,
            "median_relative_change": change,
        })
        if candidate_count >= min_candidates and change is not None and change <= stability_threshold:
            stable = True
            stopped_reason = "stable"
            break
        previous_median = current_median
        if len(raw) >= max_raw:
            stopped_reason = "max_raw"
            break

    rows = triage(raw, exclude_words)
    return {
        "queries_attempted": [batch["query"] for batch in batches],
        "raw_count": len(raw),
        "unique_count": len(rows),
        "candidate_count": sum(bool(row["candidate"]) for row in rows),
        "likely_personal_count": sum(bool(row["likely_personal"]) for row in rows),
        "likely_merchant_count": sum(bool(row["likely_merchant"]) for row in rows),
        "excluded_count": sum(bool(row["excluded_by_title"]) for row in rows),
        "median_candidate_price": median_candidate_price(rows),
        "stable": stable,
        "stopped_reason": stopped_reason,
        "batches": batches,
        "items": rows,
        "note": "Title heuristics are triage only. A model or subagent must manually retain genuinely comparable personal-seller listings.",
    }


def cache_path(state_dir: Path, config: dict) -> Path:
    digest = hashlib.sha256(json.dumps(config, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return state_dir / "cache" / f"comparables-{digest}.json"


def write_private_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)
    ignore = path.parents[1] / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n!.gitignore\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", action="append", required=True, help="Repeat 4–6 times with genuine query variants")
    parser.add_argument("--batch-limit", type=int, default=50)
    parser.add_argument("--max-raw", type=int, default=200)
    parser.add_argument("--min-candidates", type=int, default=40)
    parser.add_argument("--stability-threshold", type=float, default=0.03)
    parser.add_argument("--min-price", type=float)
    parser.add_argument("--max-price", type=float)
    parser.add_argument("--exclude-word", action="append", default=[])
    parser.add_argument("--state-dir", type=Path, default=Path(".xianyu-publish"))
    parser.add_argument("--cache-hours", type=float, default=24.0)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--fixture", type=Path, help="Offline JSON list or query-to-list mapping")
    args = parser.parse_args()

    if not 1 <= args.batch_limit <= 100:
        parser.error("--batch-limit must be between 1 and 100")
    if args.max_raw < args.batch_limit:
        parser.error("--max-raw must be at least --batch-limit")
    if not 0 <= args.stability_threshold <= 1:
        parser.error("--stability-threshold must be between 0 and 1")

    excludes = list(DEFAULT_EXCLUDE) + args.exclude_word
    config = {
        "queries": args.query,
        "batch_limit": args.batch_limit,
        "max_raw": args.max_raw,
        "min_candidates": args.min_candidates,
        "stability_threshold": args.stability_threshold,
        "min_price": args.min_price,
        "max_price": args.max_price,
        "exclude_words": excludes,
        "fixture": str(args.fixture.resolve()) if args.fixture else None,
        "schema": 2,
    }
    target = cache_path(args.state_dir, config)
    if not args.no_cache and target.exists() and time.time() - target.stat().st_mtime <= args.cache_hours * 3600:
        result = json.loads(target.read_text(encoding="utf-8"))
        result["from_cache"] = True
    else:
        searcher = fixture_searcher(args.fixture) if args.fixture else search_opencli
        result = collect(
            args.query,
            searcher,
            batch_limit=args.batch_limit,
            max_raw=args.max_raw,
            min_candidates=args.min_candidates,
            stability_threshold=args.stability_threshold,
            min_price=args.min_price,
            max_price=args.max_price,
            exclude_words=excludes,
        )
        result["from_cache"] = False
        if not args.no_cache:
            write_private_json(target, result)

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
