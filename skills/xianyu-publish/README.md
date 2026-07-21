# xianyu-publish

[简体中文](README.zh-CN.md)

A lightweight, local-first workflow that takes a personal idle item from photos to a published [Xianyu (闲鱼 / Goofish)](https://www.goofish.com) listing — then optionally keeps tracking it until it sells above your private floor.

You supply the photos and answer a few yes/no questions; the skill handles the rest — comparable-price research, a protected price plan, honest copy, publishing after your confirmation, and line-by-line verification of the live page.

## Install

```bash
npx skills add Bing-Bryan/skills-by-bing --skill xianyu-publish
```

Works with Claude Code, Codex, Cursor, and any agent supported by [`npx skills`](https://skills.sh).

## What it does

1. **Inspect & clarify** — reads your item photos and text, then asks at most five material questions (`yes / no / unknown`).
2. **Research comparables** — adaptively samples 40–60 genuine personal-seller asking prices via OpenCLI, deduplicating and excluding merchant, recycling, rental, and bait-price listings.
3. **Protected-price plan** — one recommendation: asking price, expected transaction range, a private floor kept local-only, and a trial window. Never lowers the price automatically.
4. **Honest copy** — mobile-readable listing following the 人—货—况—证—价—交 structure; owner's voice, no merchant clichés, every flaw tied to a photo.
5. **Publish on your confirmation & verify** — publishes via OpenCLI or an isolated browser once you approve, then verifies the live page line by line (Xianyu is known to collapse line breaks).
6. **Optional lightweight tracking** — daily digest of view/want deltas, diagnosis before any price-cut suggestion, and single-variable experiments observed for at least 72 hours.

## Safety model

- **Dry-run by default** — every live action (publish, edit, price change, unpublish, delete) needs explicit authorization; a price decrease always needs its own confirmation.
- **Private floor stays local** — stored with mode `0600` under `.xianyu-publish/`, never exposed to buyers or listings, deleted immediately once sold.
- **No invented claims** — never fabricates function, repair, warranty, or completeness facts; wear is disclosed, not hidden.
- **No rule circumvention** — stops on login expiry, verification, or risk control and hands the action back to you.

## Requirements

- Python 3.9+ (bundled scripts use only the standard library)
- Optional: [OpenCLI](https://github.com/jackwener/opencli) for structured Xianyu search/read/write — the skill asks before installing it; without it, photo analysis, pricing, and copywriting still work
- A browser the agent can drive, for login and visual verification

## Example prompts

- 帮我把这台相机挂到闲鱼卖掉
- 家里有件闲置，帮我看图查价、写闲鱼标题和文案
- 这部手机在闲鱼能卖多少钱？
- 帮我把这条闲鱼宝贝改价或下架
- Sell my old laptop on Xianyu — price it and write the listing
- 帮我盯一下我闲鱼链接的浏览量，每天报一次

This skill is for personal selling. It does not handle buying or bidding,
merchant bulk listings, other marketplaces, bulk scraping, or rule bypasses.

## Real-world example

- [Fujifilm X-S10 dual-lens kit: research, preflight, and live listing](examples/fujifilm-xs10/)

## Layout

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Workflow, capability ladder, operating rules |
| `references/` | Fact checklist, pricing, copywriting, monitoring specs |
| `scripts/sample_listings.py` | Adaptive comparable collection with a 24h cache |
| `scripts/listing_state.py` | Local listing state machine and metric snapshots |
| `tests/` | Offline unit tests (`python3 -m unittest discover -s tests`) |
| `examples/` | Sanitized real-world publishing examples |

## License

[MIT](LICENSE)
