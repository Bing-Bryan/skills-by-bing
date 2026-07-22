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

## Unified monitoring session

When the user requests monitoring, create exactly one recurring automation/task/session per state directory. Do not create separate daily-digest and status-check tasks, and do not create one task per item.

Use one six-hour schedule. On every run:

1. Poll the status of all monitorable user-owned items.
2. Report immediately only when an item becomes sold, paused, deleted, or unreadable.
3. On the first run at or after the user's preferred daily-report time, also produce one combined daily digest and run `purge`.
4. Persist `last_digest_date` in private local monitor metadata under the state directory so later runs that day remain silent.

Give the task a stable identity derived from the absolute state-directory path, for example `xianyu-monitor:<state-dir>`. Before creating it, inspect existing automations and update the matching task in place. Never create a duplicate because the visible task name differs. For legacy duplicates, keep one combined task and remove the others only with the user's authorization.

Use OpenCLI structured reads. Use browser DOM only for a missing field or failed adapter. Stop on verification or risk control; do not repeatedly retry. Disable the combined task only when no item in its state directory remains monitorable.

## State machine

- `active`: normal trial or observation.
- `experiment`: one authorized title, keyword, or main-image test.
- `negotiation_hold`: 48 hours after a user-reported inquiry or opt-in metadata-only conversation event; monitor status but do not change the listing.
- `paused`: item is unpublished; exclude it from normal reporting but retain local data.
- `deleted`: item was deleted; exclude it from monitoring and retain local state for the user to review or remove. Do not relabel it as paused or sold.
- `sold`: exclude it from monitoring, delete the private floor immediately, retain non-sensitive metrics for 30 days, then purge.

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
