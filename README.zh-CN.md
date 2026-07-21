# Skills by Bing

[English](README.md)

Bing Bryan 维护的个人 Agent Skills 总库。每个 Skill 位于独立目录中，可以单独安装。

## 安装

安装全部 Skills：

```bash
npx skills add Bing-Bryan/skills-by-bing
```

只安装一个 Skill：

```bash
npx skills add Bing-Bryan/skills-by-bing --skill skill-discovery-optimizer
```

支持 [`npx skills`](https://skills.sh) 所兼容的 Agent，包括 Claude Code、Cursor、Codex、Copilot 和 Gemini CLI。

## Skills 列表

| Skill | 作用 |
| --- | --- |
| [skill-discovery-optimizer](skills/skill-discovery-optimizer/) | 审阅并优化已经做好的 Agent Skill，提高它被其他 Agent 发现、正确触发、信任和安装的概率；生成中英文发布资料，并可发布到用户明确确认的 GitHub 仓库。 |

## 仓库结构

```text
skills-by-bing/
└── skills/
    └── <skill-name>/
        ├── SKILL.md
        └── 可选资源
```

仓库索引和发布文档同时维护英文与简体中文版本。

## 许可证

[MIT](LICENSE)
