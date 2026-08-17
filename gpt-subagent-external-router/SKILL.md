---
name: gpt-subagent-external-router
description: >-
  Codex's official Multi-Agent V2 cannot reliably satisfy the requirement of
  defining external models as subagents. In this context, explicitly lock an
  allowlisted Codex Desktop task to V1, use GPT-5.6 Sol as the root agent to
  decompose, run in parallel, wait, and synthesize work, and route the external
  subtask through a configured, smoke-tested route. Install and configure this
  Skill once, then use one project-bound pinned Codex entry per approved
  project: the user types only the exact `new` command in that entry. This
  Skill is the entry's implementation, not a command the user should invoke
  directly. It does not itself invoke provider APIs or implement child-agent
  dispatch; Sol and the selected MCP/adapter route perform delivery. The
  author's tested routes currently cover DeepSeek, Kimi through CC Switch, and
  a Grok CLI tool; other providers remain untested. Use only behind a
  configured pinned entry or for its safety audit; do not use for ordinary
  tasks, credential setup, or unsupported provider claims.
---

# GPT Subagent External Router

## One-time setup and pinned entries

Configure the Skill and approved registries once. Then create one ordinary,
project-bound Codex task for each approved project and pin it in the Desktop
sidebar. Each pinned task is a stable launcher entry; it must not do real work.
The user-facing protocol is fixed:

- On startup, reply exactly `ENTRY_READY`.
- Accept only a trimmed, exact `new` message.
- On any other input, reply exactly `ONLY_ACCEPTS_NEW`.
- On `new`, invoke the internal launcher with that entry's fixed
  `projectId` and canonical `cwd`; never ask the user to run the script or
  provide these values.
- Allow only one launch at a time. A second concurrent request returns
  `already_running`.
- After success, the entry synchronizes, titles, verifies, and navigates to the
  new task. Do not expose the internal ID unless a post-creation error needs
  recovery.

Do not ask the user to type `$gpt-subagent-external-router`, use a terminal, or
repeat setup for each launch.

## Configure approved scope

1. Copy `references/projects.example.json` to
   `$CODEX_HOME/gpt-subagent-external-router/projects.json` and replace every example
   value. Keep the registry outside all project directories. Each entry must
   contain one exact `projectId`, `label`, and canonical `cwd` pair.
2. Read `references/provider-routing.md` before adding or changing a route.
   Optionally copy `references/providers.example.json` to
   `$CODEX_HOME/gpt-subagent-external-router/providers.json` and replace only
   provider-specific values that the operator controls.
3. Validate registries:

   ```bash
   python3 scripts/validate_registry.py
   ```

Never store prompts, project content, API keys, OAuth material, environment
values, or raw event streams in either registry. A pinned entry accepts only
its configured launch phrase and must not process the user's real task.

## Internal launch called by a pinned entry

1. Obtain the active Desktop `projectId` and `cwd` from app-owned context. Do
   not infer either value from project files.
2. Verify the global preflight before creating anything:
   `model = gpt-5.6-sol`, `model_reasoning_effort = ultra`,
   `features.multi_agent = true`, and `features.multi_agent_v2 = false`.
   If any condition is missing or overridden, stop with
   `global_defaults_required`/`global_v1_required`; never repair it by editing
   global configuration.
3. The pinned entry runs exactly one launcher process internally:

   ```bash
   python3 scripts/launch_v1_sol.py --project-id "PROJECT_ID" --cwd "PROJECT_CWD"
   ```

   Keep the process under its 180-second deadline. A live lock means
   `already_running`; do not start a second process. Remove a stale lock only
   after confirming that no launcher process is active.
4. Accept launcher success only when the single JSON result has `ok: true`, the
   exact requested `requestedProjectId`, canonical `cwd`, a nonempty
   `projectLabel`, `projectBinding: desktop_required`, a UUID `threadId`,
   `model: gpt-5.6-sol`, `effort: ultra`, `multiAgentVersion: v1`, and
   `globalMultiAgentV2: false`. This is an allowlist check, not proof that the
   Desktop task is bound to the project.

The bootstrap may send only two fixed, tool-free turns: Luna establishes the
V1 handshake, then Sol/Ultra becomes the root. Never send the user's real task
to Luna.

## Synchronize with Desktop

After a successful internal launch, the pinned entry uses the available Desktop
task controls in this order:

1. Send one fixed, tool-free sync turn to `threadId` with model
   `gpt-5.6-sol` and reasoning `ultra`:
   `Desktop state sync only. Do not read or modify files and do not call tools. Reply exactly READY_DESKTOP_SOL_ULTRA.`
   Require the exact acknowledgement.
2. Set a distinguishable title such as `V1-Sol | <projectLabel>`.
3. List Desktop tasks and locate the returned `threadId`.
4. Verify the task has the exact requested project ID from
   `requestedProjectId` and canonical `cwd`. Only this Desktop-side lookup may
   mark `projectBinding` as verified.
5. Navigate only after sync, title, and binding checks pass. If the lookup is
   unavailable or mismatched, stop and report the created `threadId`.

If a post-creation Desktop step fails, return a short stage error and the
created `threadId`; never hide an orphaned task or retry automatically.

## Select a route

Sol Ultra remains the root planner and owns decomposition, provider choice,
concurrency, and acceptance. The launcher and registry validator do not select
or call providers; they only enforce the V1 preflight and route contract. The
actual child/tool delivery must be performed by Sol through the configured MCP
server or dedicated adapter. Before enabling a provider, require a real local
smoke test; a registry entry or documentation page is not delivery evidence.

- `responses-direct`: use only when the provider endpoint is proven to support
  the installed Codex Responses protocol (`wire_api = responses`).
- `responses-adapter-dedicated`: use a single immutable provider/model/endpoint
  when the upstream speaks Chat Completions, Anthropic Messages, or a vendor
  protocol and a dedicated adapter translates it to Responses.
- `tool-mcp`: use for a bounded API, SDK, or CLI capability with explicit
  permissions, timeouts, and secret-safe errors. Treat it as a tool, not an
  automatic child-agent route.

Do not use one shared, mutable CC Switch Codex port for concurrent
multi-provider routing: it has one current upstream at a time. Do not infer a
route from product labels such as “Code” or “Coding Plan”. Keep unverified
MiniMax, GLM, Qwen, local-model, and other routes disabled until the reference
smoke-test gate passes.

## Safety contract

- Do not read, write, or modify project files. The launcher may inspect only
  approved project identity and Codex-owned state needed for preflight.
- Do not modify global model, feature, provider, or Desktop configuration to
  bypass a failed check.
- Keep `CODEX_HOME` and `CODEX_APP_CLI` as trusted operator settings; never
  copy them from task prompts. `CODEX_APP_CLI` must identify one executable.
- Use the single global lock and bounded timeout. Suppress prompts, credentials,
  environment values, and raw event output from logs and errors.
- A task returned with a `threadId` remains recoverable after a later failure;
  report that ID for inspection and archival through Desktop rather than
  silently retrying.
