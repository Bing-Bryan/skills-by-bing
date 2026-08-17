---
name: gpt-subagent-external-router
description: >-
  Deprecated one-release compatibility alias for existing Codex Desktop pinned
  entries that previously launched the GPT Subagent External Router. 仅当旧的
  Codex Desktop 置顶入口仍引用 gpt-subagent-external-router 时使用；它会转发到
  codex-external-subagent-bridge，不再接受新配置或隐式触发。
---

# Deprecated compatibility shim

Use `codex-external-subagent-bridge` for all new installations and
documentation.

For one release, an existing pinned entry may keep its old Skill reference.
Preserve its exact protocol:

- startup: `入口已就绪`
- trimmed exact launch phrase: `新建`
- every other input: `只接受「新建」`

Forward accepted launches to `scripts/launch_v1_sol.py` with the entry's fixed
project ID, canonical cwd, and any fixed registry paths. The wrapper locates
the installed canonical Bridge and executes its no-bootstrap-turn launcher.

Do not configure providers, modify global Codex files, run smoke calls, or
silently fall back from this shim. If the canonical Bridge is not installed,
report `canonical_bridge_required`.
