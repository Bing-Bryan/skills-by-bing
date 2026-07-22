---
name: skill-discovery-optimizer
description: >-
  Audit, optimize, publish, and distribute existing Agent Skills whose core
  behavior already works. Invoke automatically as a preflight whenever the
  user asks to publish, release, sync, push, update, or upload one or multiple
  Agent Skills—or a skills monorepo—to GitHub, skills.sh, an Agent Skill
  marketplace, registry, or curated directory, even if they do not name this
  optimizer. Trigger for "把所有 Skills 更新到 GitHub", "同步 Skills 仓库并发版",
  "把这个 Skill 发布到其他技能市场", "publish these Agent Skills and verify
  installation", "audit my skill before publishing", "减少这个 Skill 的误触发",
  or "优化 Skill description 和 GitHub metadata". Review semantic routing,
  trust, installability, applicable user/repository publishing policies,
  bilingual release materials, remote installation, and listing. Do not use
  to build core functionality, install someone else's
  skill, publish an ordinary non-skill repository, do generic bilingual README
  work or web GEO/SEO, run long-term growth analytics, or publish an MCP server.
---

# Skill Discovery Optimizer

Optimize an existing Agent Skill for agent-side discovery, semantic routing, trust, installation, and launch readiness. Treat publishing as an optional final step.

优化已经可运行的 Agent Skill，使其更容易被其他 Agent 发现、理解、信任、安装和触发。发布只是可选的最后一步。

## Core model / 核心模型

Judge every change against four surfaces:

1. **Registry discovery** — searchable name, description, source metadata, and successful skills.sh listing.
2. **Semantic routing** — realistic bilingual trigger phrases and explicit negative boundaries.
3. **Trust and conversion** — safe repository, clear documentation, license, examples, and a working install command.
4. **Open-web discovery** — GitHub description/topics and relevant curated directories.

Reject changes that improve none of these surfaces. Do not confuse this work with generic content optimization.

## Workflow / 工作流

### 1. Select the operating mode

- **audit** — inspect and report only; do not edit files or write externally.
- **optimize** — edit the local skill and release materials; do not publish.
- **publish** — optimize, commit, push, and verify after the GitHub destination is confirmed.
- **distribute** — perform separately approved discovery-channel actions after publication.

Infer the narrowest mode from the request. Do not cross into a later mode without explicit user intent.

Treat a request to publish, release, sync, push, update, or upload existing Agent Skills as an automatic preflight trigger. The user does not need to mention this optimizer. For a monorepo, inspect every changed Skill and shared release surface; do not rework untouched Skills without cause. Do not trigger for ordinary repositories that merely use the word “skill.”

This is semantic implicit invocation, not an operating-system or Git hook. It works only when the optimizer is installed and implicit invocation is enabled. When another Git/GitHub publishing Skill is also relevant, run this optimizer's preflight first; let the publishing Skill perform the confirmed commit/push, then return here for remote installation and listing verification.

### 2. Inspect the target

- Require a local folder containing a working `SKILL.md` draft.
- Read applicable global and workspace instructions plus explicit user release constraints before choosing a destination or staging files.
- Turn those constraints into a release contract: canonical repository, visibility, skill path, included runtime files, excluded development files, and the disposition of any superseded repository.
- Read the full skill, its scripts/references/assets, repository documentation, and Git state.
- Preserve the skill's core behavior unless the user separately asks to change it.
- Identify target users, the concrete job, neighboring skills, and language coverage.
- Detect whether the skill already lives in a monorepo. Preserve that repository structure by default.
- Keep local validation assets available for preflight even when the release contract excludes tests, fixtures, snapshots, or test-only workflows from GitHub.

### 3. Optimize semantic discovery

- Write `description` as a routing rule: what it does, when to use it, realistic user utterances, and exclusions.
- Include complete English and Chinese example utterances when both audiences are in scope.
- Generate target-specific positive, near-negative, and ambiguous prompts dynamically. Do not depend on a fixed prompt bank.
- Keep some prompts hidden from the rewrite pass, then forward-test with a fresh agent/session when available.
- Optimize from held-out results; do not shorten metadata merely for aesthetics.
- Record each dynamic test as prompt, expected behavior, observed behavior, and rationale. Resolve every unexplained held-out mismatch.
- If a fresh session is unavailable, mark semantic forward-testing as unverified instead of claiming it passed.

### 4. Optimize searchable and trust surfaces

- Align the skill folder name and frontmatter `name`.
- Reflect the skill name and task language in the repository description, topics, and repository index. A monorepo name does not need to match each contained skill.
- Put a verified install command near the top of the repository README.
- Require clear examples, supported agents, a repository license, and a version/tag.
- Avoid opaque binaries, obfuscated code, credential collection, silent external writes, and unsafe installer patterns.

### 5. Generate bilingual release content

- Keep `README.md` as the English canonical page and link `README.zh-CN.md` near the top.
- Generate a complete `README.zh-CN.md`, not a partial summary.
- Make frontmatter `description` bilingual when both English and Chinese queries are in scope.
- Generate bilingual GitHub description and release notes where space permits.
- Keep executable instructions in one canonical language; add bilingual module docstrings, CLI help, and high-value comments rather than duplicating every code comment.

### 6. Validate locally

Run the bundled deterministic validator against the target skill folder:

```bash
python3 /path/to/skill-discovery-optimizer/scripts/validate_repo.py /absolute/path/to/target-skill --mode audit
```

Use `--mode publish` when preparing a release. In audit mode, report findings without changing files. In optimize or publish mode, fix every error and explain any remaining warning. The validator checks structure and metadata; semantic quality still requires agent judgment.

### 7. Confirm the GitHub destination

Publishing is an external write. Immediately before it:

1. Run `gh auth status` and `gh api user --jq .login`.
2. Inspect the target's Git root and `origin`; verify write access.
3. If an applicable user or workspace policy names a canonical Skill monorepo, use that repository and preserve its existing layout. Do not create or continue a standalone Skill repository unless the user explicitly overrides the policy for the current task.
4. Otherwise, if the skill already belongs to a repository, reuse that exact repository by default. Never create a second repository just because the skill was renamed.
5. If no repository exists, propose an exact `owner/repository` and visibility; create it only after explicit confirmation.
6. Show the authenticated account, exact repository, visibility, changed paths, release exclusions, and whether the operation will replace or add a skill directory.

Never infer repository ownership from Git author name or email. Continue only after the user confirms the exact destination.

### 8. Publish and verify

Build an explicit release file set before staging. Respect policy-defined exclusions: development tests may still run locally but must not be committed when the release contract excludes them. Inspect `git diff --cached --name-only` and stop if any excluded path is staged.

Commit only intended files, push to the confirmed repository, and set the approved bilingual description/topics. When migrating a Skill, verify the canonical destination before archiving or otherwise retiring the superseded repository. Then run:

```bash
python3 /path/to/skill-discovery-optimizer/scripts/verify_publish.py owner/repository --skill skill-name
```

The check must confirm remote discovery, installation inside a temporary directory, and skills.sh listing. Allow a short listing delay, but never report installation success before the remote install passes.

### 9. Distribute only when requested

- Read [references/destinations.yaml](references/destinations.yaml) and refresh stale rules before use.
- Run `scripts/distribute.py` without `--apply` to preview deterministic actions.
- Use `--apply` only after the user approves the displayed external actions.
- A real `npx skills add` initiates automatic skills.sh listing; curated directories require reviewable pull requests.
- Adapt each submission to current contribution rules. Do not mass-post generic copy or manufacture installs/stars.

## Bundled resources / 随附资源

- `scripts/validate_repo.py` — deterministic local checks / 本地机械校验。
- `scripts/verify_publish.py` — isolated remote install and listing verification / 远程隔离安装与收录验证。
- `scripts/distribute.py` — preview/apply deterministic discovery actions / 预览或执行确定性分发动作。
- [references/registries.md](references/registries.md) — registry mechanics / 注册表机制。
- [references/destinations.yaml](references/destinations.yaml) — machine-readable discovery destinations / 机器可读的发现渠道。

## Completion criteria / 完成条件

Finish only when:

- semantic routing has been reviewed with dynamic positive and negative prompts;
- the requested operating mode has not been exceeded;
- in optimize or publish mode, deterministic validation has no errors;
- in publish mode, complete English and Chinese repository documentation exists;
- if publishing was requested, the confirmed repository is live and remote installation passes;
- if distribution was requested, each external action is completed with a link or reported as awaiting third-party review.
