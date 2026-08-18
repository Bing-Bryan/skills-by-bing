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

相关的非 Skill Runtime 项目：[Codex External Subagent Runtime](https://github.com/Bing-Bryan/codex-external-subagent-runtime)，面向 Codex Desktop 的 Bootstrap、Launcher 和 Runtime Route Contract。

## Skills 列表

| Skill | 作用 |
| --- | --- |
| [parallel-imagegen](parallel-imagegen/) | 解决 Codex 生图慢的问题：在多图生成或编辑场景中，将原本需要逐张等待的任务分发到独立的 `codex exec` 进程并发执行，缩短整批图片的完成时间，并提供有界并发、失败隔离重试和证据验证。它加速的是多图任务整体，不改变单张图片的生成耗时。 |
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
