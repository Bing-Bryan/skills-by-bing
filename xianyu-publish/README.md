# xianyu-publish

[简体中文](README.zh-CN.md)

A lightweight, local-first workflow that takes a personal idle item from photos to a published [Xianyu (闲鱼 / Goofish)](https://www.goofish.com) listing — then optionally tracks its status and engagement until Xianyu reports it sold. Xianyu status does not verify the final transaction price.

You supply the photos and answer a few yes/no questions; the skill handles the rest — comparable-price research, a protected price plan, honest copy, publishing after your confirmation, and line-by-line verification of the live page.

## Install

```bash
npx skills add Bing-Bryan/skills-by-bing --skill xianyu-publish
```

Works with Claude Code, Codex, Cursor, and any agent supported by [`npx skills`](https://skills.sh).

## What it does

1. **Inspect & clarify** — reads your item photos and text, then asks at most five material questions (`yes / no / unknown`).
2. **Token-efficient comparable research** — locally aggregates about 100–200 raw search rows without sending them all to the model, then deep-reads only 15–20 highly relevant personal-seller listings for condition, bundle, asking price, engagement, and trust signals.
3. **Protected-price plan** — one recommendation: asking price, expected transaction range, a seller-only private floor shown for confirmation, and a trial window. Never lowers the price automatically.
4. **Honest copy** — mobile-readable listing following the 人—货—况—证—价—交 structure; owner's voice, no merchant clichés, every flaw tied to a photo.
5. **Publish on your confirmation & verify** — publishes via OpenCLI or an isolated browser once you approve, then verifies the live page line by line (Xianyu is known to collapse line breaks).
6. **Optional own-listing tracking** — after publication, tracks only your listing by default: daily view/want deltas, diagnosis before any price-cut suggestion, and single-variable experiments observed for at least 72 hours.

## Safety model

- **Dry-run by default** — every live action (publish, edit, price change, unpublish, delete) needs explicit authorization; a price decrease always needs its own confirmation.
- **Private floor is seller-only** — shown to you when confirming the plan, then stored with mode `0600` under `.xianyu-publish/`; omitted from routine reports, buyers, and listings, and deleted immediately once sold.
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
merchant bulk listings, other marketplaces, dataset-scale scraping, or rule
bypasses. Bounded comparable research for pricing one personal item is in scope.

## Real-world example: Fujifilm X-S10 dual-lens kit

After placing the item photos in the working directory, the user started with the single prompt below. The skill then asked only a few factual follow-ups about function, repairs, documents, lens wear, bundle-only sale, and shipping before completing research, pricing, copywriting, publishing, live verification, and lightweight monitoring.

```text
$xianyu-publish

目录文件夹里面是一个富士的 XS10 的机器，所有的信息基本上都在文件夹的图中呈现了，它有很多的图片，如果还需要其他的图片，可以找我要。

还有其他的信息，就是我的 X-S10，它配套 15-45 的变焦镜头，以及 XC35 的定焦人像镜头，总共买下来是 9390。同时，还有两颗镜头的 UV 镜，以及 XC35 的 CPL 偏振镜，三支镜片总价值 270。

除此以外，我还赠送一块原装电池以及两块绿巨能电池，价值接近 200 左右。我还附送一个绿色的相机皮套，一个手持手电筒用于拍照，以及镜头清理套组，还有一个湿度显示计，这个在我的图片上都有显示，还有一个吹灰尘的那个，那叫什么东西我还不太确定，你帮我明确一下。

就是我送这么多东西，然后你帮我看一下，当然还有一个包，还有一个皮质的松紧收束包。帮我看一下这些东西总共卖多少钱比较合适？

还有一个信息是，我这些东西都是在 23 年国庆节买的。这一点也要诚实地说上来，帮我整合闲鱼上这个品类大致的价格综合判断一下，卖多少钱比较合理？再编辑一段挂到闲鱼上的描述。

关于图片，我再补充一点。所有微信 Image 打头的是一些多角度细节图，全家福三张图是我的所有物品。细节磨损方面，三张图展现出了物品的一些轻微磨损。
```

Result: Fujifilm X-S10 + XC15-45 + XC35 F2, bought during China's 2023 National Day holiday for ¥9,390; listed at ¥6,880 with a ¥6,300–6,600 expected transaction range, using nine photos and a seven-day trial window.

Market figures are asking prices from personal Xianyu sellers, not completed-sale prices. The research image is an Agent-generated analysis view, not native Xianyu UI.

### 1. Asking-price research

![Asking-price research](https://raw.githubusercontent.com/Bing-Bryan/skills-by-bing/main/.github/assets/xianyu-publish/02-market-research.png)

### 2. Pre-publish verification

![Pre-publish verification](https://raw.githubusercontent.com/Bing-Bryan/skills-by-bing/main/.github/assets/xianyu-publish/03-publish-form-filled.png)

### 3. Live result

![Live result](https://raw.githubusercontent.com/Bing-Bryan/skills-by-bing/main/.github/assets/xianyu-publish/04-live-listing.png)

## Layout

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Workflow, capability ladder, operating rules |
| `references/` | Fact checklist, pricing, copywriting, monitoring specs |
| `scripts/sample_listings.py` | Layer 1 local aggregation with compact previews and a private 24h cache |
| `scripts/deep_read_listings.py` | Layer 2 compact deep reads for up to 20 selected comparables |
| `scripts/listing_state.py` | Local listing state machine and metric snapshots |

## License

[MIT](https://github.com/Bing-Bryan/skills-by-bing/blob/main/LICENSE)
