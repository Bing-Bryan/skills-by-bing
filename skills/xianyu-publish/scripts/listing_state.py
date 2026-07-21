#!/usr/bin/env python3
"""Manage local Xianyu listing state and lightweight metric snapshots."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from parse_utils import parse_amount as parse_number


SCHEMA_VERSION = 1
PHASES = ("active", "experiment", "negotiation_hold", "paused", "sold")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: Optional[str]) -> datetime:
    if not value:
        return now_utc()
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def ensure_state_dir(state_dir: Path) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "items").mkdir(exist_ok=True)
    ignore = state_dir / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n!.gitignore\n", encoding="utf-8")


def item_path(state_dir: Path, item_id: str) -> Path:
    if not re.fullmatch(r"\d+", str(item_id)):
        raise ValueError("item_id must contain digits only")
    ensure_state_dir(state_dir)
    return state_dir / "items" / f"{item_id}.json"


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
        path.chmod(0o600)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def load_state(state_dir: Path, item_id: str) -> dict:
    path = item_path(state_dir, item_id)
    if not path.exists():
        raise FileNotFoundError(f"state not found for item {item_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(state_dir: Path, state: dict) -> dict:
    state["updated_at"] = iso(now_utc())
    atomic_write(item_path(state_dir, str(state["item_id"])), state)
    return state


def create_state(
    item_id: str,
    title: str,
    asking_price: float,
    target_min: float,
    target_max: float,
    private_floor: float,
    trial_days: int = 7,
    at: Optional[datetime] = None,
) -> dict:
    at = at or now_utc()
    if not 1 <= trial_days <= 30:
        raise ValueError("trial_days must be between 1 and 30")
    if not (0 < private_floor <= target_max <= asking_price):
        raise ValueError("expected private_floor <= target_max <= asking_price")
    if not private_floor <= target_min <= target_max:
        raise ValueError("expected private_floor <= target_min <= target_max")
    return {
        "schema_version": SCHEMA_VERSION,
        "item_id": str(item_id),
        "title": title.strip(),
        "phase": "active",
        "created_at": iso(at),
        "updated_at": iso(at),
        "trial_days": trial_days,
        "diagnosis_due_at": iso(at + timedelta(days=trial_days)),
        "pricing": {
            "asking_price": asking_price,
            "target_min": target_min,
            "target_max": target_max,
            "private_floor": private_floor,
        },
        "negotiation_hold_until": None,
        "experiment": None,
        "retention_until": None,
        "snapshots": [],
        "events": [{"at": iso(at), "type": "initialized"}],
    }


def normalize_platform_status(value: object) -> str:
    text = str(value or "").strip().lower()
    if any(token in text for token in ("已售", "sold", "交易成功")):
        return "sold"
    if any(token in text for token in ("下架", "已下架", "paused", "unpublished", "off shelf")):
        return "paused"
    if any(token in text for token in ("删除", "deleted")):
        return "deleted"
    if any(token in text for token in ("在售", "active", "online", "selling")):
        return "active"
    return "unknown" if text else "unreadable"


def mark_sold(state: dict, at: Optional[datetime] = None) -> None:
    at = at or now_utc()
    state["phase"] = "sold"
    state["pricing"].pop("private_floor", None)
    state["negotiation_hold_until"] = None
    state["retention_until"] = iso(at + timedelta(days=30))
    state["events"].append({"at": iso(at), "type": "sold"})


def refresh_phase(state: dict, at: Optional[datetime] = None) -> None:
    at = at or now_utc()
    if state.get("phase") != "negotiation_hold":
        return
    until = parse_time(state.get("negotiation_hold_until"))
    if at >= until:
        state["phase"] = "active"
        state["negotiation_hold_until"] = None
        state["events"].append({"at": iso(at), "type": "negotiation_hold_expired"})


def add_snapshot(state: dict, snapshot: dict, at: Optional[datetime] = None) -> dict:
    at = at or now_utc()
    refresh_phase(state, at)
    platform_status = normalize_platform_status(snapshot.get("status"))
    normalized = {
        "at": iso(at),
        "platform_status": platform_status,
        "status_raw": str(snapshot.get("status") or ""),
        "price": parse_number(snapshot.get("price")),
        "views": parse_number(snapshot.get("browse_count") if "browse_count" in snapshot else snapshot.get("views")),
        "wants": parse_number(snapshot.get("want_count") if "want_count" in snapshot else snapshot.get("wants")),
        "collections": parse_number(snapshot.get("collect_count") if "collect_count" in snapshot else snapshot.get("collections")),
        "title": str(snapshot.get("title") or state.get("title") or ""),
        "image_count": parse_number(snapshot.get("image_count")),
    }
    state["snapshots"].append(normalized)
    state["snapshots"] = state["snapshots"][-180:]
    state["title"] = normalized["title"] or state.get("title", "")

    if platform_status == "sold":
        mark_sold(state, at)
    elif platform_status in ("paused", "deleted") and state.get("phase") != "sold":
        state["phase"] = "paused"
        state["events"].append({"at": iso(at), "type": platform_status})
    elif platform_status == "active" and state.get("phase") == "paused":
        state["phase"] = "active"
        state["events"].append({"at": iso(at), "type": "resumed_from_platform"})
    return normalized


def set_inquiry_hold(state: dict, hours: int = 48, at: Optional[datetime] = None) -> None:
    at = at or now_utc()
    if state.get("phase") == "sold":
        raise ValueError("cannot hold a sold item")
    state["phase"] = "negotiation_hold"
    state["negotiation_hold_until"] = iso(at + timedelta(hours=hours))
    state["events"].append({"at": iso(at), "type": "inquiry", "hold_hours": hours})


def set_phase(state: dict, phase: str, reason: str = "", at: Optional[datetime] = None) -> None:
    at = at or now_utc()
    if phase not in PHASES:
        raise ValueError(f"phase must be one of: {', '.join(PHASES)}")
    if phase == "sold":
        mark_sold(state, at)
        return
    state["phase"] = phase
    if phase != "negotiation_hold":
        state["negotiation_hold_until"] = None
    state["events"].append({"at": iso(at), "type": "phase_changed", "phase": phase, "reason": reason})


def start_experiment(
    state: dict,
    kind: str,
    variant: str,
    rollback_authorized: bool,
    hours: int = 72,
    at: Optional[datetime] = None,
) -> None:
    at = at or now_utc()
    if kind not in ("title", "keyword", "main_image"):
        raise ValueError("experiment kind must be title, keyword, or main_image")
    if state.get("phase") in ("sold", "paused", "negotiation_hold"):
        raise ValueError(f"cannot start experiment while phase is {state.get('phase')}")
    snapshots = state.get("snapshots", [])
    state["phase"] = "experiment"
    state["experiment"] = {
        "kind": kind,
        "variant": variant,
        "started_at": iso(at),
        "evaluate_after": iso(at + timedelta(hours=hours)),
        "rollback_authorized": bool(rollback_authorized),
        "baseline_snapshot_at": snapshots[-1]["at"] if snapshots else None,
    }
    state["events"].append({"at": iso(at), "type": "experiment_started", "kind": kind})


def snapshot_delta(previous: Optional[dict], current: Optional[dict], key: str) -> Optional[float]:
    if not previous or not current or previous.get(key) is None or current.get(key) is None:
        return None
    return float(current[key]) - float(previous[key])


def digest_state(state: dict, at: Optional[datetime] = None) -> dict:
    at = at or now_utc()
    refresh_phase(state, at)
    snapshots = state.get("snapshots", [])
    current = snapshots[-1] if snapshots else None
    previous = snapshots[-2] if len(snapshots) > 1 else None
    diagnosis_due = at >= parse_time(state.get("diagnosis_due_at"))
    experiment = state.get("experiment") or {}
    experiment_due = (
        state.get("phase") == "experiment"
        and bool(experiment.get("evaluate_after"))
        and at >= parse_time(experiment["evaluate_after"])
    )
    if state.get("phase") == "sold":
        conclusion = "sold"
    elif state.get("phase") == "paused":
        conclusion = "paused"
    elif current and current.get("platform_status") in ("unknown", "unreadable"):
        conclusion = "needs_attention"
    elif experiment_due:
        conclusion = "experiment_evaluation_due"
    elif diagnosis_due:
        conclusion = "diagnosis_due"
    else:
        conclusion = "continue_observing"
    return {
        "item_id": state["item_id"],
        "title": state.get("title", ""),
        "phase": state.get("phase"),
        "price": current.get("price") if current else state.get("pricing", {}).get("asking_price"),
        "views": current.get("views") if current else None,
        "views_delta": snapshot_delta(previous, current, "views"),
        "wants": current.get("wants") if current else None,
        "wants_delta": snapshot_delta(previous, current, "wants"),
        "collections": current.get("collections") if current else None,
        "collections_delta": snapshot_delta(previous, current, "collections"),
        "diagnosis_due": diagnosis_due,
        "conclusion": conclusion,
    }


def fetch_opencli_item(item_id: str) -> dict:
    cmd = [
        "opencli", "xianyu", "item", str(item_id), "-f", "json",
        "--window", "background", "--site-session", "persistent", "--keep-tab", "false",
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"item read failed: {item_id}")
    start = proc.stdout.find("[")
    if start < 0:
        raise RuntimeError("OpenCLI item output did not contain a JSON array")
    payload = json.loads(proc.stdout[start:])
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        raise RuntimeError("OpenCLI item output was empty or malformed")
    return payload[0]


def all_states(state_dir: Path) -> list[dict]:
    ensure_state_dir(state_dir)
    states = []
    for path in sorted((state_dir / "items").glob("*.json")):
        states.append(json.loads(path.read_text(encoding="utf-8")))
    return states


def print_json(payload: object) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=Path(".xianyu-publish"))
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("item_id")
    init.add_argument("--title", required=True)
    init.add_argument("--asking-price", type=float, required=True)
    init.add_argument("--target-min", type=float, required=True)
    init.add_argument("--target-max", type=float, required=True)
    init.add_argument("--private-floor", type=float, required=True)
    init.add_argument("--trial-days", type=int, default=7)

    show = sub.add_parser("show")
    show.add_argument("item_id", nargs="?")
    show.add_argument("--all", action="store_true")

    record = sub.add_parser("record")
    record.add_argument("item_id")
    record.add_argument("--fixture", type=Path, help="Offline item JSON object")

    poll = sub.add_parser("poll")
    poll.add_argument("item_id", nargs="?")
    poll.add_argument("--all", action="store_true")

    digest = sub.add_parser("digest")
    digest.add_argument("item_id", nargs="?")
    digest.add_argument("--all", action="store_true")

    inquiry = sub.add_parser("inquiry")
    inquiry.add_argument("item_id")
    inquiry.add_argument("--hours", type=int, default=48)

    phase = sub.add_parser("phase")
    phase.add_argument("item_id")
    phase.add_argument("value", choices=PHASES)
    phase.add_argument("--reason", default="")

    experiment = sub.add_parser("experiment")
    experiment.add_argument("item_id")
    experiment.add_argument("--kind", choices=("title", "keyword", "main_image"), required=True)
    experiment.add_argument("--variant", required=True)
    experiment.add_argument("--rollback-authorized", action="store_true")
    experiment.add_argument("--hours", type=int, default=72)

    sub.add_parser("purge")
    args = parser.parse_args()

    if args.command == "init":
        state = create_state(
            args.item_id, args.title, args.asking_price, args.target_min,
            args.target_max, args.private_floor, args.trial_days,
        )
        save_state(args.state_dir, state)
        print_json(state)
        return 0

    if args.command == "show":
        if args.all:
            print_json(all_states(args.state_dir))
        elif args.item_id:
            print_json(load_state(args.state_dir, args.item_id))
        else:
            parser.error("show requires item_id or --all")
        return 0

    if args.command in ("record", "poll"):
        item_ids = [state["item_id"] for state in all_states(args.state_dir)] if getattr(args, "all", False) else [args.item_id]
        if not item_ids or any(item_id is None for item_id in item_ids):
            parser.error(f"{args.command} requires item_id or --all")
        results = []
        fixture_payload = None
        if args.command == "record":
            if not args.fixture:
                parser.error("record requires --fixture")
            fixture_payload = json.loads(args.fixture.read_text(encoding="utf-8"))
        for item_id in item_ids:
            state = load_state(args.state_dir, item_id)
            payload = fixture_payload if args.command == "record" else fetch_opencli_item(item_id)
            snapshot = add_snapshot(state, payload)
            save_state(args.state_dir, state)
            results.append({"item_id": item_id, "snapshot": snapshot, "phase": state["phase"]})
        print_json(results[0] if len(results) == 1 else results)
        return 0

    if args.command == "digest":
        states = all_states(args.state_dir) if args.all else [load_state(args.state_dir, args.item_id)] if args.item_id else []
        if not states:
            parser.error("digest requires item_id or --all")
        print_json([digest_state(state) for state in states])
        return 0

    if args.command == "inquiry":
        state = load_state(args.state_dir, args.item_id)
        set_inquiry_hold(state, args.hours)
        save_state(args.state_dir, state)
        print_json(state)
        return 0

    if args.command == "phase":
        state = load_state(args.state_dir, args.item_id)
        set_phase(state, args.value, args.reason)
        save_state(args.state_dir, state)
        print_json(state)
        return 0

    if args.command == "experiment":
        state = load_state(args.state_dir, args.item_id)
        start_experiment(state, args.kind, args.variant, args.rollback_authorized, args.hours)
        save_state(args.state_dir, state)
        print_json(state)
        return 0

    if args.command == "purge":
        removed = []
        at = now_utc()
        for state in all_states(args.state_dir):
            retention = state.get("retention_until")
            if state.get("phase") == "sold" and retention and at >= parse_time(retention):
                path = item_path(args.state_dir, state["item_id"])
                path.unlink(missing_ok=True)
                removed.append(state["item_id"])
        print_json({"removed": removed})
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
