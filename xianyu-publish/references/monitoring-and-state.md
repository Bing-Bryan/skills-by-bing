# Lightweight monitoring and local state

## Scope

Default monitoring reports only:

- item status: active, paused/unpublished, sold, deleted, or unreadable;
- current price;
- total views and daily delta;
- total wants/collections and daily deltas;
- whether a diagnosis checkpoint is due;
- one conclusion: `continue observing` or one recommended action.

Monitor user-owned listings only. Do not continue polling the pre-publish comparable set after the user's listing goes live.

Do not monitor private chat content, platform impressions, CTR, recommendation sources, or global search rank. Search-position and experiment details are opt-in diagnostics, not daily-report defaults.

## Schedule

When the user requests monitoring, create two lightweight local schedules with whatever scheduler the host agent provides (scheduled tasks, cron, or equivalent):

1. Daily digest: poll all active items once per day and send one combined report.
2. Status check: every six hours, inspect status only; remain silent unless the item becomes sold, paused, deleted, or unreadable.

Use OpenCLI structured reads. Use browser DOM only for a missing field or failed adapter. Stop on verification or risk control; do not repeatedly retry.

## State machine

- `active`: normal trial or observation.
- `experiment`: one authorized title, keyword, or main-image test.
- `negotiation_hold`: 48 hours after a user-reported inquiry or opt-in metadata-only conversation event; monitor status but do not change the listing.
- `paused`: item is unpublished; stop normal reporting but retain local data.
- `deleted`: item was deleted; stop schedules and retain local state for the user to review or remove. Do not relabel it as paused or sold.
- `sold`: stop schedules, delete the private floor immediately, retain non-sensitive metrics for 30 days, then purge.

Do not treat `paused/unpublished` as sold. Ask when the platform status is ambiguous. If a hold expires and the item remains active, return to `active`.

## Local storage

Use `scripts/listing_state.py` with a user-selected workspace or its default `.xianyu-publish` directory. Store one JSON file per item with mode `0600`; create a local `.gitignore`; never use cloud storage.

Typical commands, resolved from the skill directory:

```bash
python3 scripts/listing_state.py --state-dir PATH init ITEM_ID --title TITLE --asking-price ASK --target-min MIN --target-max MAX --private-floor FLOOR
python3 scripts/listing_state.py --state-dir PATH poll --all
python3 scripts/listing_state.py --state-dir PATH digest --all
python3 scripts/listing_state.py --state-dir PATH inquiry ITEM_ID
python3 scripts/listing_state.py --state-dir PATH purge
```

Run `purge` with the daily digest so sold-item metrics expire after 30 days.

For multiple items, keep independent state and experiments but merge normal reporting into one digest. The business goal is a sale above the private floor, but the platform status cannot verify the final transaction price; views, wants, collections, and conversations are only process signals.
