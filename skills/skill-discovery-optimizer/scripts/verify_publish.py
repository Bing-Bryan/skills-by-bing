#!/usr/bin/env python3
"""Verify remote Agent Skill discovery and installation in isolation.

在隔离目录中验证远程 Agent Skill 的发现、安装和 skills.sh 收录。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def listing_url(source: str, skill: str) -> str | None:
    parts = source.removeprefix("https://github.com/").removesuffix(".git").strip("/").split("/")
    if len(parts) != 2:
        return None
    # Use the canonical host directly because macOS system Python does not
    # consistently follow skills.sh's HTTP 308 redirect. / 直接使用规范域名，
    # 避免 macOS 系统 Python 未跟随 skills.sh 的 HTTP 308 重定向。
    return f"https://www.skills.sh/{parts[0]}/{parts[1]}/{skill}"


def url_exists(url: str) -> bool:
    request = urllib.request.Request(url, headers={"User-Agent": "skill-discovery-optimizer/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status == 200 and "skills.sh" in response.geturl()
    except (urllib.error.URLError, TimeoutError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a published Agent Skill / 验证已发布的 Agent Skill")
    parser.add_argument("source", help="GitHub owner/repository, URL, or local path / GitHub 仓库、URL 或本地路径")
    parser.add_argument("--skill", required=True, help="Frontmatter skill name / Skill 的 frontmatter name")
    parser.add_argument("--wait-seconds", type=int, default=45, help="Wait for skills.sh listing / 等待 skills.sh 收录秒数")
    parser.add_argument("--skip-listing", action="store_true", help="Skip skills.sh check for local tests / 本地测试时跳过 skills.sh")
    parser.add_argument("--json", action="store_true", help="Emit JSON / 输出 JSON")
    args = parser.parse_args()

    if not shutil.which("npx"):
        print("npx is required / 缺少 npx", file=sys.stderr)
        return 2

    report: dict[str, object] = {"source": args.source, "skill": args.skill}
    listed = run(["npx", "--yes", "skills", "add", args.source, "--list"])
    report["remote_discovery"] = listed.returncode == 0 and args.skill.lower() in (listed.stdout + listed.stderr).lower()
    report["remote_discovery_log"] = (listed.stdout + listed.stderr).strip()[-2000:]

    with tempfile.TemporaryDirectory(prefix="skill-publish-check-") as temp:
        temp_path = Path(temp)
        installed = run(
            ["npx", "--yes", "skills", "add", args.source, "--skill", args.skill, "--agent", "universal", "--copy", "-y"],
            cwd=temp_path,
        )
        installed_file = temp_path / ".agents" / "skills" / args.skill / "SKILL.md"
        report["install_exit_code"] = installed.returncode
        report["isolated_install"] = installed.returncode == 0 and installed_file.is_file()
        report["install_log"] = (installed.stdout + installed.stderr).strip()[-3000:]

    url = listing_url(args.source, args.skill)
    report["skills_sh_url"] = url
    if args.skip_listing or url is None:
        report["skills_sh_listed"] = None
    else:
        deadline = time.monotonic() + max(0, args.wait_seconds)
        found = url_exists(url)
        while not found and time.monotonic() < deadline:
            time.sleep(5)
            found = url_exists(url)
        report["skills_sh_listed"] = found

    success = bool(report["remote_discovery"] and report["isolated_install"])
    if report.get("skills_sh_listed") is False:
        success = False
    report["success"] = success

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Remote discovery / 远程发现: {'PASS' if report['remote_discovery'] else 'FAIL'}")
        print(f"Isolated install / 隔离安装: {'PASS' if report['isolated_install'] else 'FAIL'}")
        if report.get("skills_sh_listed") is not None:
            print(f"skills.sh listing / skills.sh 收录: {'PASS' if report['skills_sh_listed'] else 'FAIL'}")
        if url:
            print(url)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
