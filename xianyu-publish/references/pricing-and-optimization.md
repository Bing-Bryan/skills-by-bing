# Pricing and optimization

## Protected-price plan

Produce four values:

1. `asking_price`: the public trial price, normally above the target range to allow negotiation.
2. `target_range`: the evidence-supported expected transaction range.
3. `private_floor`: a model recommendation confirmed by the user and stored only locally.
4. `trial_days`: default seven days; shorten for liquid items and extend to 10–14 days for expensive, sparse, or niche markets.

Do not let a low comparable median force a low asking price. Adjust for condition, bundle, accessories, scarcity, seller evidence, and negotiation room. Explain premiums rather than hiding them. Never recommend or execute a price below the confirmed floor.

## Pre-publish evidence weighting

- Use the Layer 1 local aggregate to establish the broad asking-price distribution without loading full search rows into model context.
- Use 15–20 Layer 2 deep reads to judge actual comparability: model/variant, condition, bundle, description quality, images, and seller trust.
- Weight price, condition, and bundle most heavily. Use wants, views, collections, and search rank only as supporting signals because listing age and exposure are unknown.
- Treat `sold` status as a status signal only. Neither displayed price nor a backend field named `soldPrice` proves the final transaction amount.
- After publication, stop competitor research and monitor the user's own listing unless the user separately requests a new market check.

## Diagnose before lowering

Use observable signals as proxies, not causal proof:

- Low view growth: inspect search discoverability, title, keywords, category, and main image before price.
- Normal views but weak wants/collections: inspect trust facts, condition clarity, bundle, and price.
- Wants/collections rising but no inquiry: consider a small price or transaction-term change.
- After an inquiry: enter a 48-hour negotiation hold; do not alter the listing during that period.
- Insufficient volume: say `insufficient evidence` and extend observation up to the trial-window boundary.

The platform does not expose reliable impressions, CTR, recommendation sources, global rank, or competitor transaction prices. Do not claim them.

## Single-variable experiments

1. Save the current listing and metric snapshot as the baseline.
2. Propose one change only: title, keyword composition, or main image.
3. Obtain one explicit authorization for the experiment.
4. Observe at least 72 hours; extend when volume is insufficient.
5. Compare view growth, wants/collections per view, new item-linked conversations when available, and consistent-query search position only as noisy proxies.
6. Keep an improving variant. If it clearly worsens, automatically recommend or perform only the pre-authorized rollback.
7. Require new authorization for another variant. Require separate authorization for every price decrease.

## Main-image rules

Prefer a clear, honest subject, useful scale, uncluttered background, and visible bundle completeness. Allow selection, ordering, crop, straightening, and mild exposure or white-balance correction. Do not erase defects, generate missing product details, replace the item, or add merchant-style promotional stickers by default.
