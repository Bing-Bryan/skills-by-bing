# Registry mechanics / 注册表机制

Last verified / 最后核实：2026-07-21

## GitHub

GitHub is the recommended public source for Agent Skills, not a universal registry. A repository should expose a valid `SKILL.md`, bilingual human-facing documentation, an install command, a license, a concise description, and relevant topics.

GitHub 是 Agent Skill 推荐的公开源码载体，不是统一注册表。仓库应提供有效的 `SKILL.md`、中英双语说明、安装命令、许可证、简介和相关 Topics。

## skills.sh

- Ordinary Git-hosted Agent Skills have no separate submission form.
- A telemetry-enabled `npx skills add owner/repository` installation initiates automatic listing.
- Installation telemetry drives listing counts; never fabricate installs.
- Verify the remote artifact with `scripts/verify_publish.py` and allow a short indexing delay.

- 普通 Git 托管 Skill 不需要单独投稿。
- 启用遥测的 `npx skills add owner/repository` 会触发自动收录。
- 安装遥测会影响安装量；禁止伪造安装。
- 使用 `scripts/verify_publish.py` 验证远程产物，并允许短暂索引延迟。

Official references / 官方资料：

- https://skills.sh/docs/faq
- https://skills.sh/docs/cli
- https://github.com/vercel-labs/skills

## MCP Registry exclusion / MCP Registry 排除说明

The official MCP Registry publishes MCP Server metadata, not ordinary `SKILL.md` packages. It is outside this skill's scope.

官方 MCP Registry 发布的是 MCP Server 元数据，不收录普通 `SKILL.md`，因此不属于本 Skill 的范围。
