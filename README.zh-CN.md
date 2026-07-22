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
| [parallel-imagegen](parallel-imagegen/) | 通过彼此独立的 `codex exec` 进程，并发执行内置 Codex 图片生成或编辑任务，并提供有界 Worker、失败隔离重试和证据验证。 |
| [skill-discovery-optimizer](skill-discovery-optimizer/) | 通过发布前的检查、优化与验证，让 Skill 更容易被 Agent 发现、准确触发并顺利安装。 |
| [xianyu-publish](xianyu-publish/) | 面向闲鱼个人卖家的本地优先工作流：看图查价、保价定价、诚实文案，经确认后发布、核对并轻量跟踪。 |

## 仓库结构

```text
skills-by-bing/
└── <skill-name>/
    ├── SKILL.md
    └── 可选资源
```

仓库索引和发布文档同时维护英文与简体中文版本。

## 许可证

[MIT](LICENSE)
