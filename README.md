# Skills by Bing

[Simplified Chinese](README.zh-CN.md)

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

Install the Codex Desktop bridge specifically:

```bash
npx skills add Bing-Bryan/skills-by-bing --skill codex-external-subagent-bridge
```

Works with agents supported by [`npx skills`](https://skills.sh), including Claude Code, Cursor, Codex, Copilot, and Gemini CLI.

## Available Skills

| Skill | What it does |
| --- | --- |
| [parallel-imagegen](parallel-imagegen/) | Solves slow Codex image generation for multi-image workflows. Instead of waiting for images one by one, it runs independent generation or editing tasks concurrently across separate `codex exec` processes, reducing total batch completion time with bounded concurrency, isolated retries, and evidence-backed verification. It speeds up the overall multi-image workflow, not a single image. |
| [skill-discovery-optimizer](skill-discovery-optimizer/) | Through pre-publish checks, optimization, and verification, it makes Skills easier for Agents to discover, invoke correctly, and install successfully. |
| [codex-external-subagent-bridge](codex-external-subagent-bridge/) | Codex Desktop-only launcher and route-contract bridge. A project-pinned exact lowercase `new` entry creates a zero-bootstrap-turn V1 task as GPT-5.6 Luna, switches it to GPT-5.6 Sol Ultra, and exposes only enabled, locally smoke-tested, fingerprint-matching existing child or MCP routes. Users define their own providers; the Skill does not modify provider, MCP, Keychain, CC Switch, or global model configuration. |
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
