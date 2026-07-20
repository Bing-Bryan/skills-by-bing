#!/usr/bin/env python3
"""Validate deterministic Agent Skill publishing requirements.

校验 Agent Skill 发布前可以机械判断的要求；语义质量仍由 Agent 审阅。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CJK_RE = re.compile(r"[\u3400-\u9fff]")
ENGLISH_RE = re.compile(r"[A-Za-z]{3,}")


@dataclass
class Finding:
    severity: str
    code: str
    message_en: str
    message_zh: str


def add(findings: list[Finding], severity: str, code: str, en: str, zh: str) -> None:
    findings.append(Finding(severity, code, en, zh))


def repository_root(skill_dir: Path) -> tuple[Path, bool]:
    result = subprocess.run(
        ["git", "-C", str(skill_dir), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return Path(result.stdout.strip()), True
    return skill_dir, False


def load_frontmatter(skill_file: Path) -> tuple[dict[str, Any], str | None]:
    text = skill_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "SKILL.md must start with YAML frontmatter"
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return {}, "YAML frontmatter is not closed"

    raw = "\n".join(lines[1:end])
    if shutil.which("ruby"):
        ruby = (
            "require 'yaml'; require 'json'; "
            "value = YAML.safe_load(STDIN.read, permitted_classes: [], aliases: false); "
            "puts JSON.generate(value || {})"
        )
        result = subprocess.run(
            ["ruby", "-e", ruby], input=raw, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            return {}, result.stderr.strip() or "Strict YAML parsing failed"
        try:
            value = json.loads(result.stdout)
            return value if isinstance(value, dict) else {}, None
        except json.JSONDecodeError as exc:
            return {}, f"Strict YAML output was invalid: {exc}"

    # Portable fallback for required fields only. / 仅解析必需字段的可移植回退。
    name_match = re.search(r'(?m)^name:\s*[\'\"]?([^\'\"\n]+)[\'\"]?\s*$', raw)
    desc_match = re.search(
        r"(?ms)^description:\s*(?:[>|]-?\s*\n(?P<block>(?:^[ \t]+.*\n?)*)|(?P<plain>.+))",
        raw,
    )
    data: dict[str, Any] = {}
    if name_match:
        data["name"] = name_match.group(1).strip()
    if desc_match:
        description = desc_match.group("block") or desc_match.group("plain") or ""
        data["description"] = " ".join(line.strip() for line in description.splitlines()).strip(" '\"")
    return data, None


def inspect_remote(repo: str, findings: list[Finding]) -> None:
    if not shutil.which("gh"):
        add(findings, "warning", "gh-missing", "GitHub CLI unavailable; remote metadata was not checked.", "未安装 GitHub CLI，无法检查远程元数据。")
        return
    result = subprocess.run(
        ["gh", "repo", "view", repo, "--json", "description,repositoryTopics,visibility,url"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        add(findings, "error", "repo-unreachable", f"Cannot access GitHub repository {repo}.", f"无法访问 GitHub 仓库 {repo}。")
        return
    metadata = json.loads(result.stdout)
    if not (metadata.get("description") or "").strip():
        add(findings, "error", "github-description", "GitHub repository description is empty.", "GitHub 仓库简介为空。")
    if len(metadata.get("repositoryTopics") or []) < 3:
        add(findings, "warning", "github-topics", "Use at least three relevant GitHub topics.", "建议至少设置三个相关 GitHub Topics。")


def validate(skill_dir: Path, repo: str | None, mode: str) -> list[Finding]:
    findings: list[Finding] = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        add(findings, "error", "skill-file", "SKILL.md is missing.", "缺少 SKILL.md。")
        return findings

    metadata, yaml_error = load_frontmatter(skill_file)
    if yaml_error:
        add(findings, "error", "frontmatter-yaml", yaml_error, f"YAML 解析失败：{yaml_error}")
        return findings

    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        add(findings, "error", "name-format", "Frontmatter name must use lowercase hyphen-case.", "Frontmatter name 必须使用小写连字符格式。")
    elif skill_dir.name != name:
        add(findings, "error", "name-folder", f"Folder '{skill_dir.name}' does not match name '{name}'.", f"目录名“{skill_dir.name}”与 name“{name}”不一致。")

    if not isinstance(description, str) or len(description.strip()) < 80:
        add(findings, "error", "description-short", "Description is missing or too short to route reliably.", "Description 缺失或过短，无法可靠路由。")
    elif not (CJK_RE.search(description) and ENGLISH_RE.search(description)):
        add(findings, "error", "description-bilingual", "Description must contain natural English and Chinese trigger language.", "Description 必须包含自然的中英文触发表达。")

    root, in_git_repo = repository_root(skill_dir)
    readme_en = root / "README.md"
    readme_zh = root / "README.zh-CN.md"
    license_files = [root / "LICENSE", root / "LICENSE.md", root / "LICENSE.txt"]

    release_severity = "error" if mode == "publish" else "warning"
    if not in_git_repo and mode == "audit":
        add(findings, "warning", "repo-context", "The target is not inside a Git repository; repository release metadata cannot be fully audited.", "目标不在 Git 仓库中，无法完整审阅仓库发布元数据。")

    if not readme_en.is_file():
        add(findings, release_severity, "readme-en", "README.md is required for publishing.", "发布时需要 README.md。")
    else:
        readme = readme_en.read_text(encoding="utf-8", errors="replace")
        if "README.zh-CN.md" not in readme:
            add(findings, release_severity, "readme-language-link", "README.md must link to README.zh-CN.md near the top for publishing.", "发布时 README.md 顶部必须链接 README.zh-CN.md。")
        if "npx skills add" not in readme:
            add(findings, release_severity, "install-command", "README.md must contain an npx skills install command for publishing.", "发布时 README.md 必须包含 npx skills 安装命令。")

    if not readme_zh.is_file():
        add(findings, release_severity, "readme-zh", "README.zh-CN.md is required for publishing.", "发布时需要 README.zh-CN.md。")
    if not any(path.is_file() for path in license_files):
        add(findings, release_severity, "license", "A repository license is required for publishing.", "发布时仓库必须包含许可证。")

    suspicious_names = {".env", "id_rsa", "id_ed25519", "credentials.json", "secrets.json"}
    for path in root.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        if path.name in suspicious_names or path.suffix.lower() in {".pem", ".p12", ".key"}:
            add(findings, "error", "secret-file", f"Potential secret file: {path.relative_to(root)}", f"发现疑似密钥文件：{path.relative_to(root)}")

    if repo:
        inspect_remote(repo, findings)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an Agent Skill repository / 校验 Agent Skill 仓库")
    parser.add_argument("path", type=Path, help="Skill folder containing SKILL.md / 包含 SKILL.md 的目录")
    parser.add_argument("--repo", help="Optional GitHub owner/repository / 可选 GitHub owner/repository")
    parser.add_argument("--mode", choices=("audit", "publish"), default="audit", help="Validation strictness / 校验严格程度")
    parser.add_argument("--json", action="store_true", help="Emit JSON / 输出 JSON")
    args = parser.parse_args()

    path = args.path.expanduser().resolve()
    findings = validate(path, args.repo, args.mode)
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    if args.json:
        print(json.dumps({"path": str(path), "errors": errors, "warnings": warnings, "findings": [asdict(item) for item in findings]}, ensure_ascii=False, indent=2))
    else:
        for item in findings:
            print(f"[{item.severity.upper()}] {item.code}: {item.message_en} / {item.message_zh}")
        print(f"Result: {errors} error(s), {warnings} warning(s) / 结果：{errors} 个错误，{warnings} 个警告")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
