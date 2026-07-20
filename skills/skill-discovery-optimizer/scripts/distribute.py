#!/usr/bin/env python3
"""Preview or apply deterministic Agent Skill discovery actions.

预览或执行确定性的 Agent Skill 发现渠道动作；第三方投稿仍需审核。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
DESTINATIONS = SKILL_DIR / "references" / "destinations.yaml"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan/apply Agent Skill distribution / 规划或执行 Agent Skill 分发")
    parser.add_argument("repo", help="GitHub owner/repository / GitHub owner/repository")
    parser.add_argument("--skill", required=True, help="Skill name / Skill 名称")
    parser.add_argument("--description", required=True, help="Bilingual GitHub description / 中英双语 GitHub 简介")
    parser.add_argument("--topics", nargs="+", default=["agent-skills", "skill-discovery", "codex", "ai-agents"], help="GitHub topics")
    parser.add_argument("--apply", action="store_true", help="Apply GitHub metadata and first-install verification / 应用 GitHub 元数据并执行首次安装验证")
    args = parser.parse_args()

    config = json.loads(DESTINATIONS.read_text(encoding="utf-8"))
    plan = {
        "repo": args.repo,
        "skill": args.skill,
        "automatic": ["Set GitHub description/topics", "Run isolated npx skills add", "Verify skills.sh listing"],
        "approval_gated": [item for item in config["destinations"] if item.get("approval_required")],
    }
    if not args.apply:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        print("Preview only. Re-run with --apply after user approval. / 当前仅预览，用户确认后添加 --apply。")
        return 0

    if not shutil.which("gh"):
        print("gh is required / 缺少 gh", file=sys.stderr)
        return 2
    if run(["gh", "auth", "status"]).returncode != 0:
        print("GitHub authentication failed / GitHub 身份验证失败", file=sys.stderr)
        return 2
    if run(["gh", "repo", "view", args.repo, "--json", "nameWithOwner"]).returncode != 0:
        print(f"Repository is not accessible: {args.repo} / 无法访问仓库：{args.repo}", file=sys.stderr)
        return 2

    edit = run(["gh", "repo", "edit", args.repo, "--description", args.description])
    if edit.returncode != 0:
        print(edit.stderr, file=sys.stderr)
        return 1
    for topic in args.topics:
        result = run(["gh", "repo", "edit", args.repo, "--add-topic", topic])
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return 1

    verify = run([sys.executable, str(SKILL_DIR / "scripts" / "verify_publish.py"), args.repo, "--skill", args.skill])
    print(verify.stdout)
    if verify.returncode != 0:
        print(verify.stderr, file=sys.stderr)
        return verify.returncode

    print("Deterministic distribution completed. Curated-list PRs still require agent adaptation and user-approved submission.")
    print("确定性分发已完成；精选目录 PR 仍需 Agent 按当前规则适配，并经用户确认后提交。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
