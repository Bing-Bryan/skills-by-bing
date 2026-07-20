---
name: agent-geo
description: >-
  Use when the user built, or is about to publish, their own GitHub repo, agent skill (SKILL.md), or MCP server, and wants OTHER people's AI agents (Claude Code, Cursor, Codex, etc.) — not just humans — to find it, install it, trust it, and call it. This is always the creator/publisher/growth side, never someone hunting for an existing skill to install. Recognize casual, jargon-free phrasing just as strongly as the word "GEO": "我做了个 skill/工具，怎么让别人的 AI/agent 用上它"、"发出去了零 star 零安装，冷启动怎么搞"、"有什么套路能让 agent 优先找到我的仓库"、"准备传几个小工具到 GitHub，怎么弄能让 Cursor/Claude Code 优先用上"、"怕发了没人装，发布前帮我看看要注意什么"、"README/GitHub topics/SKILL.md description 怎么写才能被 agent 检索到"、"skills.sh 的排名到底是怎么算的"、"为什么我的仓库别人的 agent 搜不到"、"how do I get my repo or skills discovered and used by other agents"、"published my skill but zero installs, how do I get traction". Answers informational questions about ecosystem mechanics (skills.sh ranking, install counts, find-skills trust thresholds) as well as hands-on tasks. Also covers monorepo vs many small repos, awesome-list submission, and auditing an already-published repo for discoverability gaps. Do NOT use for finding/installing someone else's existing skill (that's find-skills), building an agent's actual functionality, or generic website/app SEO, ASO, or ad spend unrelated to agent skills/MCP servers.
---

# Agent GEO：让仓库和 skill 被 agent 发现并调用

## 工作流

1. 判断用户处于哪个阶段：**写作**（skill/README 还没写）、**发布**（结构与元数据）、**推广**（冷启动）、**审计**（已发布，求诊断）。只讲当前阶段需要的部分。
2. 涉及具体数字或排名时，先打开 skills.sh 核实现状再回答（见下节原因）。
3. 按 Playbook 执行或对照 Checklist 审计，给一个明确建议，不给选项菜单。

## 心智模型：三个检索面

Agent 时代的 GEO 不是优化 Google，是优化三个检索面，重要性从高到低：

1. **注册表排名**（skills.sh / MCP registry）——agent 找 skill 的默认路径
2. **description 语义路由**——agent 决定"要不要用你"时唯一读到的文本
3. **开放 web 与训练数据**——搜索引擎、教程、awesome list；长线复利

任何优化动作都应能归入其中一个面；归不进去的动作大概率无效。

## 机制事实（2026-07 实测，引用前先刷新）

数字漂移很快（曾观察到一个月内总量 +25 万），**向用户报数字前先打开 skills.sh 看实况**；机制本身相对稳定：

- skills.sh（Vercel）：开放注册表，自动收录、无提交审核，**纯安装量遥测排名**；排行榜**按仓库聚合展示**（"+N more from owner/repo (X total)"）。2026-07 收录约 92 万 skill。
- `npx skills` CLI 支持 70+ 个 agent（Claude Code、Codex、Cursor、Copilot、Gemini CLI、Qwen Code、Trae 等）：一份标准 SKILL.md 发一次，覆盖几乎全部主流 coding agent。
- find-skills skill（装机 250 万+，agent 侧发现机制的事实标准）内置信任门槛：**安装量 <100 慎用、1K+ 优先；仓库 <100 star 被要求"持怀疑态度"**；官方组织信誉加分。
- Claude Code 会话启动只加载每个 skill 的 name + description（约 100 token）；触发与否完全取决于 description 与用户原话的语义匹配。
- skills.sh 对收录内容跑安全扫描（Socket / Snyk 等）。
- skill 源不限 GitHub：GitLab、任意 git URL、自有域名都能装（飞书官方就用 open.feishu.cn）；但 GitHub star 参与信任评估，无特殊理由默认 GitHub。

## Playbook（按优先级）

### 1. Monorepo，不要撒仓库

排行榜按仓库聚合 + <100 star 触发怀疑，意味着 20 个散仓库每个 10 star 会全部卡在信任线下；一个 monorepo 把 star 和安装量聚合起来，每个 skill 仍可单独安装（`owner/repo@skill-name`）。参照 anthropics/skills、vercel-labs/agent-skills；mattpocock/skills 证明个人 monorepo 也能进排行榜前 20。

### 2. description 当路由规则写，不当宣传语写

公式：**做什么 + 什么时候用 + 用户会说的原话触发词（含同义词；目标用户双语就写双语）+ 边界（"不负责 X，走 Y"）**。它是写给路由器看的，宣传语零权重。写完必须实测：构造若干"该触发"和"不该触发"的 prompt 验证两个方向，近似领域的负例（共享关键词但不该触发）最有价值。

2026-07 对本 skill 自身做过 5 轮触发率 A/B 实测（20 条双语 query、留出测试集选优），四条经验直接可复用：

- 触发词写成**引号包裹的完整原话例句**，不要关键词罗列——例句版在留出集上胜出
- **疑问句/信息型 query 天然弱触发**（模型倾向直接回答而不查 skill）：想接住"X 是怎么回事"类问题，必须显式放疑问句例句
- **例句语言 = 用户提问语言**：框架句用什么语言无所谓（语义路由跨语言），但例句匹配是语言敏感的——只放中文例句时英文 query 触发率接近零。面向谁发布，就放谁的语言的例句
- 实测要**留几条 prompt 不给改写过程看**：对着失败案例补词会"背题"——见过的题分数涨、新题分数跌
- **"发布要裁短"这条实测证伪了，不要裁**：2026-07 曾把本 skill 的 description 从 1318 字符裁到 626（同类例句每类只留 1 条，类别覆盖不丢），做 A/B 实测——同一批 20 条 query、负例 precision 两版都是 100% 不变，但正例召回从 6/10 掉到 4/10。裁短买到的是省 token 和列表页好看，代价是实打实漏掉真实提问；这笔交易不划算。description 长度不该按"头部 skill 平均多长"这种参照系定，只按实测留出集分数定——分数不掉才能裁，裁完必须重测
- 真要省上下文，省在**正文**：正文是按需加载的（触发后才读），不占安装者的常驻上下文；description 这块是唯一持续收租的地方，租金换召回，这笔账划算

### 3. 关键词进检索位

`npx skills find` 是关键词搜索。目标查询词要出现在：skill 目录名、frontmatter name、description、仓库 description、GitHub topics（`claude-code`、`agent-skills`、`claude-skills`、`mcp` 加领域词）。

### 4. README 首屏为 agent 优化

第一句话说清"给谁、解决什么"；一键安装命令置顶——agent 抓到 README 后会直接复制命令执行，命令离顶部越近越好。注明支持的 agent 范围。

### 5. 信任信号是硬门槛，不是加分项

LICENSE、持续的 commit 记录、版本 tag。skill 内不放 `curl | bash`、混淆代码、可疑外联——安全扫描会标红，被标红的 skill agent 不会推荐。

### 6. 冷启动：排名 = 安装量，安装量需要初始分发

- 发布后自己先 `npx skills add owner/repo` 一次：既验证可安装，也确认被 skills.sh 收录（收录是自动的，无需提交）。
- 提交 awesome list：ComposioHQ/awesome-claude-skills（find-skills 源码明文引用它）、heilcheng/awesome-agent-skills 等。
- 写发布文和教程，让安装命令出现在别人的内容里。
- 不刷量：排名机制可被 game，但作弊会随生态治理变成尾部风险，不值得。

### 7. 选位：细分词第一，好过大词第五十

避开官方已入场的位置（例：飞书官方以 930 万总安装占据 lark 生态，个人做 lark skill 没有位置）。找"有真实查询、无强势玩家"的缝隙词。命名独特可记忆，避免与头部 skill 撞名。

### 8. 长线

有 docs 站就加 llms.txt；高 star 仓库最终进入模型训练数据，未来的 agent 会"天生记得你"。这是复利，但解决不了冷启动，别把宝押在这。

## 发布前 Checklist

逐项过，全绿再发：

- [ ] frontmatter 规范：name 全小写连字符；description 含触发词与边界
- [ ] frontmatter 能过**严格 YAML 解析**：description 含 `: `（冒号+空格）或引号时必须用 `>-` 块标量包裹。本地 agent 解析宽容不报错 ≠ 注册表能收录——2026-07 实测：裸写的 description 因内含 `"GEO": "` 被 `npx skills` 判为 "No skills found"，仓库推上去了却装不了
- [ ] description 双向实测通过（该触发的触发，不该触发的不触发；例句含中英双语和疑问句，留几条没参与改写的 prompt 做终检）
- [ ] README 首屏有一键安装命令
- [ ] 仓库 description 与 topics 填满
- [ ] LICENSE 与版本 tag 齐全
- [ ] 无任何会触发安全扫描的内容
- [ ] 自己 add 一次安装成功，skills.sh 能搜到
- [ ] 已提交至少 2 个 awesome list

## MCP server 分支

逻辑相同，注册表不同：发布到官方 MCP registry，再覆盖 Smithery、PulseMCP 等社区注册表。server 和每个 tool 的 name / description 同样是 agent 的检索面，套用第 2 条的 description 纪律。
