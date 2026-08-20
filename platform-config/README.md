# Platform config

A Console Home-maintained fork of the [Daijishō](https://github.com/TapiocaFox/Daijishou)
platform/emulator configuration database (`platforms/` index + per-platform manifests), hosted
under [`console-home-public`](https://github.com/techwithnidhi/console-home-public) alongside this
project's other public assets.

Console Home's live platform-config fetch and bundled offline snapshot previously pointed
directly at the upstream `TapiocaFox/Daijishou` repo — a third party we don't control, with no
ability to fix stale entries or add new platforms without waiting on (or forking) upstream. This
directory is that fork: a schema-compatible source Console Home can maintain going forward.

## Contents

- `index.json` — the platform index (`{ baseUri, platformList: [...] }`), matching Daijishō's
  `DaijishoIndex` shape.
- `platforms/<uniqueId>.json` — one manifest per platform (`{ databaseVersion, revisionNumber,
  platform: {...}, playerList: [...] }`), matching Daijishō's `DaijishoPlatformManifest` shape.
- `scripts/convert_seed_to_daijisho.py` — the conversion script that generated `index.json` and
  `platforms/*.json` from the source seed data.
- `scripts/platforms_seed.json` — a committed copy of the source seed data (Console Home's
  bundled `platforms_seed.json` snapshot) so the conversion script is self-contained and can be
  re-run without needing a `console-home` checkout on hand.
- `scripts/verify_conversion.py` — verifies the generated output against the seed: content
  equivalence (names, shortnames, regexes, player order) and schema validity (non-null
  constraints, `revisionNumber`, entry/file counts).

This is a **faithful, mechanical conversion** — same 120 platforms, same `uniqueId`s, same player
entries in the same order, no additions/removals/renames. `packageName` is intentionally dropped
from each player entry: it is not part of the Daijishō schema and is re-derived by the consuming
app from `amStartArguments` at parse time.

## `baseUri`

`index.json`'s `baseUri` is set to this directory's raw content root:
`https://raw.githubusercontent.com/techwithnidhi/console-home-public/main/platform-config`.
**Not** a URL ending in `/platforms` — each index entry's `filename` already carries the
`platforms/` prefix (e.g. `platforms/3do.json`), and the consuming app joins
`baseUri.trimEnd('/') + "/" + filename`, so a `/platforms`-suffixed `baseUri` would double that
path segment and 404.

## Re-running the conversion

If the source seed data changes upstream (in the `console-home` app repo), re-run the conversion
against a fresh copy:

```sh
python3 scripts/convert_seed_to_daijisho.py /path/to/updated/platforms_seed.json
python3 scripts/verify_conversion.py /path/to/updated/platforms_seed.json
```

Both scripts default to `scripts/platforms_seed.json` (the committed copy) when no path is given.
JSON output is written with stable key ordering, 2-space indentation, and a trailing newline, so
re-runs against unchanged input produce byte-identical output.

## `revisionNumber`

Every index entry and manifest ships `revisionNumber: 1`, never `0`. The seed data's own
`revisionNumber` field is always `0` and is intentionally **not** copied verbatim: the consuming
app's staleness guard skips updates when `existing.revisionNumber >= incoming.revisionNumber`, so
shipping `0` would make every platform permanently un-fetchable (even under a forced sync) the
moment anything points at this repo.

## License / attribution

This repo's platform data is a substantial derivative of Daijishō's MIT-licensed `platforms/`
database (TapiocaFox / Yves Chen, 2022). See `LICENSE` — the original MIT notice is preserved
per the license's notice-preservation requirement, alongside a Console Home copyright line for
this repo's structure, scripts, and any subsequent edits.

Nothing from CocoonFE's fork is used or referenced here.

## Status

Published under `console-home-public/platform-config`. `PlatformApiService.PLATFORM_INDEX_URL` in
the `console-home` app repo points at this directory's `index.json`.
