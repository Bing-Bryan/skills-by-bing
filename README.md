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
| [parallel-imagegen](parallel-imagegen/) | Runs independent built-in Codex image generation or editing jobs concurrently through separate `codex exec` processes, with bounded workers, isolated retries, and evidence-based verification. |
| [skill-discovery-optimizer](skill-discovery-optimizer/) | Through pre-publish checks, optimization, and verification, it makes Skills easier for Agents to discover, invoke correctly, and install successfully. |
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
