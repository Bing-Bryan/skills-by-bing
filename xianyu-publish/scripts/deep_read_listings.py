#!/usr/bin/env python3
"""Deep-read up to 20 Xianyu comparables and emit a compact local summary."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional

from parse_utils import parse_amount, parse_price


def parse_json_array(output: str) -> list[dict]:
    start = output.find("[")
    if start < 0:
        raise ValueError("OpenCLI output did not contain a JSON array")
    payload = json.loads(output[start:])
    if not isinstance(payload, list):
        raise ValueError("OpenCLI item output must be a JSON array")
    return [item for item in payload if isinstance(item, dict)]


def fetch_opencli(item_id: str) -> dict:
    cmd = [
        "opencli", "xianyu", "item", item_id, "-f", "json",
        "--window", "background", "--site-session", "persistent", "--keep-tab", "false",
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"item read failed: {item_id}")
    rows = parse_json_array(proc.stdout)
    if not rows:
        raise RuntimeError(f"item read returned no data: {item_id}")
    return rows[0]


def load_fixture(path: Path, item_ids: Iterable[str]) -> tuple[list[dict], list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_id = {
        str(item.get("item_id", "")): item
        for item in (payload.values() if isinstance(payload, dict) else payload)
        if isinstance(item, dict)
    }
    rows = []
    errors = []
    for item_id in item_ids:
        if item_id in by_id:
            rows.append(by_id[item_id])
        else:
            errors.append({"item_id": item_id, "error": "missing from fixture"})
    return rows, errors


def percentile(values: Iterable[float], fraction: float) -> Optional[float]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def numeric_summary(values: Iterable[Optional[float]]) -> dict:
    numbers = [float(value) for value in values if value is not None]
    return {
        "count": len(numbers),
        "min": min(numbers) if numbers else None,
        "p25": percentile(numbers, 0.25),
        "median": statistics.median(numbers) if numbers else None,
        "p75": percentile(numbers, 0.75),
        "max": max(numbers) if numbers else None,
    }


def compact_item(item: dict, description_chars: int) -> dict:
    description = re.sub(r"\s+", " ", str(item.get("description", ""))).strip()
    views = parse_amount(item.get("browse_count"))
    wants = parse_amount(item.get("want_count"))
    return {
        "item_id": str(item.get("item_id", "")),
        "title": str(item.get("title", "")),
        "price": parse_price(item.get("price")),
        "original_price": parse_price(item.get("original_price")),
        "want_count": wants,
        "collect_count": parse_amount(item.get("collect_count")),
        "browse_count": views,
        "want_view_ratio": wants / views if wants is not None and views else None,
        "status": str(item.get("status", "")),
        "condition": str(item.get("condition", "")),
        "brand": str(item.get("brand", "")),
        "category": str(item.get("category", "")),
        "location": str(item.get("location", "")),
        "seller_score": str(item.get("seller_score", "")),
        "reply_ratio_24h": str(item.get("reply_ratio_24h", "")),
        "reply_interval": str(item.get("reply_interval", "")),
        "image_count": parse_amount(item.get("image_count")),
        "description_excerpt": description[:description_chars],
        "item_url": str(item.get("item_url", "")),
    }


def summarize(items: Iterable[dict], errors: Iterable[dict] = (), description_chars: int = 280) -> dict:
    compact = [compact_item(item, description_chars) for item in items]
    error_rows = list(errors)
    return {
        "requested_count": len(compact) + len(error_rows),
        "fetched_count": len(compact),
        "price_summary": numeric_summary(item["price"] for item in compact),
        "want_summary": numeric_summary(item["want_count"] for item in compact),
        "browse_summary": numeric_summary(item["browse_count"] for item in compact),
        "collect_summary": numeric_summary(item["collect_count"] for item in compact),
        "want_view_ratio_summary": numeric_summary(item["want_view_ratio"] for item in compact),
        "status_counts": dict(Counter(item["status"] or "unknown" for item in compact)),
        "items": compact,
        "errors": error_rows,
        "note": (
            "Prices are displayed asking prices, not verified transaction prices. Static want, browse, "
            "and collect counts are supporting signals only. Full details and image URLs remain local."
        ),
    }


def cache_path(state_dir: Path, item_ids: Iterable[str]) -> Path:
    key = json.dumps({"item_ids": list(item_ids), "schema": 1}, sort_keys=True)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return state_dir / "cache" / f"deep-comparables-{digest}.json"


def write_private_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)
    ignore = path.parents[1] / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n!.gitignore\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item-id", action="append", required=True, help="Repeat for 15–20 selected comparables")
    parser.add_argument("--state-dir", type=Path, default=Path(".xianyu-publish"))
    parser.add_argument("--cache-hours", type=float, default=24.0)
    parser.add_argument("--description-chars", type=int, default=280)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--include-full", action="store_true", help="Include full item payloads for debugging")
    parser.add_argument("--fixture", type=Path, help="Offline JSON list or item-id mapping")
    args = parser.parse_args()

    item_ids = list(dict.fromkeys(str(item_id).strip() for item_id in args.item_id))
    if any(not re.fullmatch(r"\d+", item_id) for item_id in item_ids):
        parser.error("every --item-id must contain digits only")
    if not 1 <= len(item_ids) <= 20:
        parser.error("provide between 1 and 20 unique item IDs")
    if not 80 <= args.description_chars <= 600:
        parser.error("--description-chars must be between 80 and 600")

    target = cache_path(args.state_dir, item_ids)
    from_cache = False
    if not args.no_cache and target.exists() and time.time() - target.stat().st_mtime <= args.cache_hours * 3600:
        cached = json.loads(target.read_text(encoding="utf-8"))
        items = cached.get("items", [])
        errors = cached.get("errors", [])
        from_cache = True
    elif args.fixture:
        items, errors = load_fixture(args.fixture, item_ids)
    else:
        items = []
        errors = []
        for item_id in item_ids:
            try:
                items.append(fetch_opencli(item_id))
            except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
                errors.append({"item_id": item_id, "error": str(exc)})

    if not from_cache and not args.no_cache:
        write_private_json(target, {"items": items, "errors": errors})

    output = summarize(items, errors, args.description_chars)
    output["from_cache"] = from_cache
    output["cache_file"] = str(target) if not args.no_cache else None
    if args.include_full:
        output["full_items"] = items
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if items else 1


if __name__ == "__main__":
    raise SystemExit(main())
