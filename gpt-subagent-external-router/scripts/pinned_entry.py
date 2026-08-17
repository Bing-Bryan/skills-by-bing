#!/usr/bin/env python3
"""Forward the legacy deterministic entry path to the canonical Bridge."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def candidates() -> tuple[Path, ...]:
    raw_home = os.environ.get("CODEX_HOME")
    home = Path(raw_home).expanduser().resolve() if raw_home else (Path.home() / ".codex").resolve()
    here = Path(__file__).resolve()
    return (
        here.parents[2] / "codex-external-subagent-bridge" / "scripts" / "pinned_entry.py",
        home / "skills" / "codex-external-subagent-bridge" / "scripts" / "pinned_entry.py",
        Path.home() / ".agents" / "skills" / "codex-external-subagent-bridge" / "scripts" / "pinned_entry.py",
    )


def main() -> int:
    for candidate in candidates():
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            continue
        if resolved.is_file():
            os.execv(sys.executable, [sys.executable, str(resolved), *sys.argv[1:]])
    print('{"ok":false,"error":"canonical_bridge_required"}', file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
