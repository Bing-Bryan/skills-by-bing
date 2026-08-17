# Skills by Bing

[简体中文](README.zh-CN.md)

A personal monorepo of Agent Skills maintained by Bing Bryan. Each Skill lives in its own folder and can be installed independently.

## Install

Install all Skills:

```bash
npx skills add Bing-Bryan/skills-by-bing
```

Install one Skill:

```bash
npx skills add Bing-Bryan/skills-by-bing --skill skill-discovery-optimizer
```

Works with agents supported by [`npx skills`](https://skills.sh), including Claude Code, Cursor, Codex, Copilot, and Gemini CLI.

## Available Skills

| Skill | What it does |
| --- | --- |
| [parallel-imagegen](parallel-imagegen/) | Solves slow Codex image generation for multi-image workflows. Instead of waiting for images one by one, it runs independent generation or editing tasks concurrently across separate `codex exec` processes, reducing total batch completion time with bounded concurrency, isolated retries, and evidence-backed verification. It speeds up the overall multi-image workflow, not a single image. |
| [skill-discovery-optimizer](skill-discovery-optimizer/) | Through pre-publish checks, optimization, and verification, it makes Skills easier for Agents to discover, invoke correctly, and install successfully. |
| [gpt-subagent-external-router](gpt-subagent-external-router/) | Codex's official Multi-Agent V2 cannot reliably satisfy the requirement of defining external models as subagents; in this context, this Skill explicitly locks the task to V1, uses GPT-5.6 Sol as the root agent to decompose, run in parallel, wait, and synthesize work, and provides a contract for routing external subtasks through smoke-tested routes. The launcher does not implement provider dispatch. The author's tested routes currently cover DeepSeek, Kimi through CC Switch, and a Grok CLI tool; other providers remain untested. |
| [xianyu-publish](xianyu-publish/) | A local-first workflow for personal Xianyu sellers: inspect photos, research comparables, protect pricing, write honest copy, publish after confirmation, verify, and track lightly. |

## Repository structure

```text
skills-by-bing/
└── <skill-name>/
    ├── SKILL.md
    └── optional resources
```

The repository index and release documentation are maintained in English and Simplified Chinese.

## License

[MIT](LICENSE)
