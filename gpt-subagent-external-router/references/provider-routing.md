# Provider routing contract

Use this reference to classify an external route by protocol, execution semantics, and evidence. Keep Sol Ultra as the root planner. Keep provider configuration separate from the V1 bootstrap.

## Why this V1 path exists

Multi-Agent V2 can route among supported OpenAI model roles, but an installed V2 runtime may use OpenAI-specific child context or payloads that a third-party provider cannot consume. Treat that as a version-specific interoperability gap, not a permanent prohibition. Use this Skill only after real task delivery through the intended V2 external route fails or is known to be incompatible.

V1 supplies the external child-agent compatibility path. It does not erase provider protocol differences: every external child still needs a verified Responses endpoint or a dedicated adapter.

This repository's launcher and registry validator do not call provider APIs or
dispatch child agents. They enforce the V1 preflight and routing contract;
Sol, together with the selected MCP server or dedicated adapter, performs the
actual delivery.

## Contents

- [Transport classes](#transport-classes)
- [Product names are not protocols](#product-names-are-not-protocols)
- [CC Switch boundary](#cc-switch-boundary)
- [Author-deployed evidence](#author-deployed-evidence)
- [Documentation-only candidates](#documentation-only-candidates)
- [Registry status meanings](#registry-status-meanings)
- [Smoke-test gate](#smoke-test-gate)

## Transport classes

| Transport | Use when | Required boundary |
| --- | --- | --- |
| `responses-direct` | The provider endpoint is proven to implement the Responses API used by the installed Codex build. | One stable provider identity, model ID, and credential environment variable. |
| `responses-adapter-dedicated` | The upstream exposes Chat Completions, Anthropic Messages, or a vendor-native protocol. | One immutable Responses adapter and port per provider; never switch its upstream during a task. |
| `tool-mcp` | An API, SDK, or CLI capability should be exposed as a bounded tool instead of a full child. | Narrow schema, explicit permissions and timeouts, secret-safe errors, and no arbitrary command execution. |

Codex `wire_api` must be `responses`. Do not configure `chat` and do not assume that an OpenAI-shaped Chat Completions endpoint is sufficient.

## Product names are not protocols

Do not infer transport from labels such as “Code,” “Coding Plan,” or “OpenAI compatible.” A Code-branded product is neither required nor sufficient for MCP. A stable API, SDK, or non-interactive CLI can be wrapped as an MCP tool; a browser-only product cannot be treated as routable merely because it has a coding UI.

Keep these semantics distinct:

- A Responses endpoint or adapter can support a full V1 model child.
- An MCP wrapper exposes a capability as a tool. It does not automatically provide child-agent identity, lifecycle, context inheritance, or concurrency semantics.
- A CLI is an implementation detail. Wrap it behind MCP or a dedicated adapter before presenting it as a stable route.

## CC Switch boundary

CC Switch can store multiple providers, but one shared Codex proxy port has one current upstream. Changing that upstream is global mutable state. Two agents using the same port can therefore race or be sent to the wrong provider.

Safe choices:

1. A provider's native, verified Responses endpoint.
2. A provider-specific Responses adapter on a dedicated immutable port.
3. A bounded MCP tool when the backend is exposed through OAuth/CLI rather than a compatible model API.

Do not claim deterministic concurrent routing through one shared CC Switch Codex port.

## Author-deployed evidence

This table describes the author's local evidence as of **2026-08-17**. It is not a portability guarantee.

| Provider | Route proven by the author | Evidence boundary |
| --- | --- | --- |
| DeepSeek | V1 model child through the author's direct-provider pattern | Real task delivery completed. Reverify the endpoint, model ID, provider identity, and response in every installation. |
| Kimi | V1 model child while CC Switch remains fixed to Kimi | Real task delivery completed. One shared mutable CC Switch port is not deterministic concurrent routing; a dedicated Kimi endpoint remains unproven. |
| Grok | Read-only public-X MCP tool backed by OAuth/CLI | Real bounded tool delivery completed. The private wrapper and credentials are not shipped; this is not Grok Build and not a model child. |

No other provider has been deployed or smoke-tested by the author.

## Documentation-only candidates

Treat every row below as disabled until local smoke tests pass.

| Provider or product | Candidate route from official documentation | Author evidence |
| --- | --- | --- |
| MiniMax Codex/Token Plan | `responses-direct` through its documented Responses endpoint | Not tried |
| GLM / Z.ai Codex | `responses-direct`; verify the exact regional product endpoint and raw Responses behavior | Not tried |
| Qwen Model Studio, Token Plan, or PAYG | `responses-direct` when the selected regional endpoint explicitly supports Responses | Not tried |
| Qwen Coding Plan | `responses-adapter-dedicated` for its Chat Completions or Anthropic Messages endpoint, or a bounded `tool-mcp` wrapper | Not tried |
| Local open-weight models | Direct only when the serving layer implements the required Responses protocol; otherwise use a dedicated adapter | Not tried |

Official vendor references: [MiniMax Responses API](https://platform.minimax.io/docs/api-reference/responses-create), [MiniMax Codex guide](https://platform.minimax.io/docs/token-plan/codex), [Z.AI Codex guide](https://docs.z.ai/devpack/tool/codex), [Qwen Responses API](https://www.alibabacloud.com/help/en/model-studio/compatibility-with-openai-responses-api), [Qwen Codex guide](https://help.aliyun.com/en/model-studio/codex), and [Qwen Coding Plan FAQ](https://www.alibabacloud.com/help/en/model-studio/coding-plan-faq).

## Registry status meanings

- `verified-pattern`: the author has real task-delivery evidence for the exact pattern, not universal support for every account or endpoint.
- `conditional`: a bounded route worked only under stated conditions, or the safer target architecture is not fully proven.
- `experimental`: official documentation or design analysis suggests a route, but the author has not deployed it.

## Smoke-test gate

Before Sol may choose a new provider route, verify all of the following:

1. **Protocol:** a real Responses request completes without translation errors.
2. **Identity:** persisted task metadata or provider evidence identifies the intended provider and model.
3. **Delivery:** the child or tool returns a task-specific sentinel, not merely a successful spawn.
4. **Isolation:** two different providers can run concurrently without a shared mutable upstream.
5. **Failure:** timeout, auth failure, or malformed output stops safely without retrying through another provider.
6. **Privacy:** logs and errors contain no prompts, environment values, credentials, or raw event streams.

If any check fails, keep that route disabled. Do not change global defaults or enable Multi-Agent V2 as a workaround.

Official references: [Codex App Server](https://developers.openai.com/codex/app-server/) and [Codex configuration reference](https://developers.openai.com/codex/config-reference/).
