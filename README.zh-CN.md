# Skill Discovery Optimizer

[English](README.md)

审阅并优化已经做好的 Agent Skill，提高它被其他 Agent 发现、理解、信任、安装和触发的概率。发布只是可选的最后一步。

## 安装

```bash
npx skills add 1767249060-creator/skill-discovery-optimizer --skill skill-discovery-optimizer
```

支持 [`npx skills`](https://skills.sh) 所兼容的 Agent。

## 能做什么

- 审阅已经完成或接近完成的 Agent Skill，不改变其核心功能。
- 优化名称、路由 description、触发边界、仓库元数据、信任信号和安装路径。
- 生成完整的英文和简体中文发布文档。
- 执行确定性仓库校验和新会话语义路由测试。
- 可选发布到用户明确确认的 GitHub 仓库，验证远程隔离安装，并触发 skills.sh 收录。
- 预览精选目录投稿；第三方 PR 仍需单独确认。

## 工作模式

```text
只读审阅 → 本地优化 → 发布到确认的 GitHub 仓库 → 分发
```

本 Skill 只执行用户请求的最窄模式：审阅不授权修改文件，本地优化也不授权公开发布。

## 范围

| Skill | 作用 |
| --- | --- |
| [skill-discovery-optimizer](skills/skill-discovery-optimizer/) | 审阅并优化已经做好的 Agent Skill，提高它被其他 Agent 发现、正确触发、信任和安装的概率；生成中英文发布资料，并可发布到用户明确确认的 GitHub 仓库。 |

它不负责构建 Skill 的核心功能、安装别人的 Skill、通用网站 GEO/SEO、长期增长监控或 MCP Server 发布。

## 环境要求

- Python 3.10+
- Node.js 与 `npx`
- 仅在发布时需要已认证的 GitHub CLI（`gh`）

## 许可证

[MIT](LICENSE)
