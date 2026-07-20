# Skill Discovery Optimizer

[简体中文](README.zh-CN.md)

Review and optimize a finished Agent Skill so other agents can discover, understand, trust, install, and trigger it. Publishing is an optional final step.

## Install

```bash
npx skills add 1767249060-creator/skill-discovery-optimizer --skill skill-discovery-optimizer
```

Works with any agent supported by [`npx skills`](https://skills.sh) — Claude Code, Cursor, Codex, Copilot, Gemini CLI, and more.

## What it does

- Audits a completed or near-completed Agent Skill without changing its core behavior.
- Improves its name, routing description, trigger boundaries, repository metadata, trust signals, and installation path.
- Generates complete English and Simplified Chinese release documentation.
- Runs deterministic repository checks and fresh-session semantic routing tests.
- Optionally publishes to an explicitly confirmed GitHub repository, verifies an isolated remote install, and initiates skills.sh listing.
- Previews curated-directory submissions; third-party pull requests remain approval-gated.

## Operating modes

```text
Audit only → Optimize locally → Publish to confirmed GitHub repo → Distribute
```

The skill uses the narrowest mode requested. A review request does not authorize file edits, and a local optimization request does not authorize publishing.

## Scope

| Skill | What it does |
| --- | --- |
| [skill-discovery-optimizer](skills/skill-discovery-optimizer/) | Reviews and optimizes a finished Agent Skill for agent-side discovery, routing, trust, and installation. Generates bilingual release materials and can publish to a confirmed GitHub repository. |

It does not build a Skill's core functionality, install other people's Skills, perform generic website GEO/SEO, run long-term growth analytics, or publish MCP servers.

## Requirements

- Python 3.10+
- Node.js and `npx`
- Authenticated GitHub CLI (`gh`) only when publishing

## License

[MIT](LICENSE)
