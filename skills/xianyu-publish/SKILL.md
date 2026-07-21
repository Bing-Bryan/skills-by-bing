---
name: xianyu-publish
description: >-
  Sell, price, publish, edit, unpublish, monitor, and optimize personal
  secondhand listings on Xianyu (闲鱼 / Goofish). Use for requests such as
  "帮我把这台相机挂到闲鱼卖掉", "家里闲置帮我看图查价、写标题和文案",
  "这部手机在闲鱼能卖多少", "闲鱼改价/下架", "帮我盯浏览量和想要数",
  "sell my old laptop on Goofish", or when the user wants an end-to-end
  personal-sale workflow: inspect photos, clarify facts, research comparable
  asking prices, protect a private floor, draft honest copy, publish only after
  confirmation, verify the live page, and lightly track the listing. Use only
  when the user is or intends to be the personal seller. If seller/owner role
  or personal-versus-commercial scope is unclear, clarify before routing. Do
  not use for buying or bidding, merchant/store or bulk listings, other
  marketplaces such as 转转/Taobao/eBay, dataset-scale scraping, or bypassing
  platform rules. Bounded comparable research for pricing one personal item
  remains in scope.
---

# Xianyu Publish（闲鱼发布）

Help ordinary users sell personal items with little effort. Let the model handle judgment; use deterministic tools for collection, state, publishing, and verification. Optimize for an eventual sale above the user's private floor, not merchant-style growth.

## Capability ladder

1. Use OpenCLI for structured search, item reads, unattended monitoring, and supported writes.
2. Use an isolated browser for login, unsupported fields, complex edits, and visual verification.
3. Without OpenCLI or an authenticated account, still finish photo analysis, pricing, and copy; stop before unsupported publishing or monitoring.
4. Ask before installing OpenCLI (`@jackwener/opencli`, Apache-2.0, https://github.com/jackwener/opencli). Treat it as an external optional dependency; do not vendor or fork it.

## Core workflow

1. Inspect supplied photos and text. Identify the item, variant, included parts, visible wear, and uncertain claims.
2. Check obvious prohibited-item, infringement, and platform-rule risks. Refuse circumvention.
3. Ask at most five material follow-up questions. Prefer `yes / no / unknown`; read [references/field-checklist.md](references/field-checklist.md).
4. For a new listing or substantive change, run the research gate below. Skip it for typo, spacing, line-break, and faithful render repairs.
5. Build one recommended plan: asking price, expected transaction range, private floor, trial window, title, canonical copy, and photo order. Follow [references/pricing-and-optimization.md](references/pricing-and-optimization.md) and [references/copywriting.md](references/copywriting.md).
6. Show the recommendation first and keep evidence collapsible. Never expose the private floor to buyers or the listing. If you generate a useful local HTML report, visualization, or other review artifact, open it in the agent's default internal browser when available and show it to the user as evidence; also provide a direct file link or screenshot. Label AI-generated artifacts clearly and never present them as native Xianyu UI.
7. After showing the final plan, if the user's requested outcome includes a live publish, edit, price change, unpublish, or delete action, proactively ask one explicit authorization question that names the action and key values. Do not wait for the user to volunteer another command. Treat the initial request as intent, not final approval; a price decrease always needs separate confirmation.
8. Publish with OpenCLI when supported; otherwise use the isolated browser. Preserve one canonical copy for both confirmation and publication.
9. Verify the live URL, price, images, category, condition, shipping, and copy line by line. Repair rendering before reporting completion.
10. After successful live verification, proactively offer lightweight monitoring once and briefly explain the daily metric digest and silent status checks. Only if the user accepts—or has already requested monitoring—initialize local state and create the schedules in [references/monitoring-and-state.md](references/monitoring-and-state.md).

## Adaptive research gate

Before drafting new copy or making a substantive change to title, positioning, price, claims, structure, or transaction terms:

1. Spawn a subagent; prohibit it from modifying the live listing.
2. Search 4–6 genuine query variants in batches of roughly 40–60 raw results. Use `scripts/sample_listings.py` when OpenCLI is available.
3. Deduplicate by item ID and exclude merchants, recycling, rental, accessories-only, software/service, bait-price, and unrelated-model listings.
4. Prefer 40–60 retained personal-seller comparables. Stop when another batch no longer materially changes the price band or observed copy patterns.
5. Treat about 200 raw results as a ceiling, not a target. If the market is sparse, report the actual sample; never invent counts.
6. Reuse a matching cache for up to 24 hours.
7. Report raw, unique, candidate, and manually retained counts plus 3–5 representative item IDs. Treat observed prices as asking prices, never confirmed transaction prices.

## Operating rules

- Treat the workflow as dry-run until the user explicitly authorizes a named live action. Proactively request that authorization at the transition to a live action; dry-run is a write guard, not a reason to wait silently. If the user requests `dry-run`, prohibit all writes for that run even if earlier authorization exists.
- Default to price protection: seven-day trial, adjusted by liquidity; never lower automatically.
- Diagnose before recommending a price cut. Time only triggers a review.
- Change one title, keyword, or main-image variable per experiment. Observe at least 72 hours and allow `insufficient evidence`.
- Require one authorization per new experiment. Monitoring and an authorized rollback may run automatically; a new variant may not.
- Optimize photos only by selection, order, crop, straightening, and mild exposure/white-balance correction. Never hide wear or synthesize product facts.
- Do not read buyer chat content by default. A user-reported inquiry—or optional metadata-only detection—starts a 48-hour negotiation hold; if the item remains active afterward, resume operation.
- Keep multiple items independent but combine normal daily reporting into one scheduled job.

## Safety and recovery

- Never invent function, repair, water, impact, component, usage-count, invoice, warranty, or completeness claims.
- Associate visible flaws with specific photos. Avoid unnecessary serial-number exposure.
- Preserve platform remedies for misdescription. Use: `个人闲置，一经售出不提供质保或长期售后；如与描述不符，按平台规则处理。`
- Keep precise addresses and private floors local and out of conversation unless strictly necessary.
- On login expiry, verification, risk control, or selector failure: retry once, stop, preserve state, and give one clear user action. Never bypass controls.

## User-facing output

Keep normal output to one screen:

- recommended asking price, transaction range, private floor, and trial days;
- one-sentence rationale;
- up to five unresolved facts;
- final title and copy;
- an opened review artifact when one was generated, clearly labeled as AI-generated rather than native platform UI;
- publish or monitoring status;
- when a live action is ready, one explicit approval question naming the action and key values;
- after successful live verification, one optional monitoring offer; otherwise at most one evidence-based recommended action.
