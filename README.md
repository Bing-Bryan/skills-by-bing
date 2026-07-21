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
| [skill-discovery-optimizer](skills/skill-discovery-optimizer/) | Reviews and optimizes a finished Agent Skill for agent-side discovery, routing, trust, and installation. Generates bilingual release materials and can publish to a confirmed GitHub repository. |

## Repository structure

```text
skills-by-bing/
└── skills/
    └── <skill-name>/
        ├── SKILL.md
        └── optional resources
```

The repository index and release documentation are maintained in English and Simplified Chinese.

## License

[MIT](LICENSE)
