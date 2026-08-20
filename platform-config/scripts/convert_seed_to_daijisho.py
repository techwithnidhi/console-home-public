#!/usr/bin/env python3
"""Convert the Console Home bundled platforms_seed.json into a Daijishō-schema
config repo layout: root index.json + one manifest file per platform under
platforms/.

Usage:
    python3 scripts/convert_seed_to_daijisho.py <path-to-platforms_seed.json>

If no path is given, defaults to scripts/platforms_seed.json (the committed
input copy in this repo), so the script is self-contained and re-runnable
without needing a console-home checkout on hand.

Faithful, mechanical field mapping — see the plan's Research section. No
renames, no drops of uniqueIds, no reordering that would change filenames
across a re-run (stable sort by id).

revisionNumber is NOT copied from the seed — every seed row is 0, and
PlatformRepository.kt's staleness guard (`existing.revisionNumber >=
entry.revisionNumber` -> skip) means an index/manifest revisionNumber of 0
would make every platform un-fetchable FOREVER, even under a forced sync,
once anything ever points at this repo. Emit 1 for every platform, both in
the index entry and the manifest's top-level revisionNumber (kept equal to
each other).
"""

import json
import os
import sys

SEED_REVISION = 1
DATABASE_VERSION = 1


def convert(seed_platforms: list[dict]) -> tuple[dict, dict[str, dict]]:
    index_entries = []
    manifests = {}
    for p in sorted(seed_platforms, key=lambda x: x["id"]):
        uid = p["id"]
        filename = f"platforms/{uid}.json"
        index_entries.append({
            "filename": filename,
            "platformName": p["name"],
            "platformShortname": p["shortName"],
            "platformUniqueId": uid,
            "revisionNumber": SEED_REVISION,
        })
        manifests[filename] = {
            "databaseVersion": DATABASE_VERSION,
            "revisionNumber": SEED_REVISION,
            "platform": {
                "name": p["name"],
                "uniqueId": uid,
                "shortname": p["shortName"],
                "acceptedFilenameRegex": p.get("acceptedFilenameRegex"),
            },
            # players[] may legitimately be empty (e.g. "elektor") — that's valid, not an error.
            # Order is preserved (no sorting within a platform's player list).
            "playerList": [
                {
                    "name": pl["name"],
                    "uniqueId": pl["uniqueId"],
                    "amStartArguments": pl["amStartArguments"],
                    "acceptedFilenameRegex": pl.get("acceptedFilenameRegex"),
                }
                for pl in p.get("players", [])
            ],
        }
    return {"baseUri": "<TODO: set on publish — must be the repo RAW ROOT, not .../platforms>", "platformList": index_entries}, manifests


def write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def main() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if len(sys.argv) > 1:
        seed_path = sys.argv[1]
    else:
        seed_path = os.path.join(repo_root, "scripts", "platforms_seed.json")

    with open(seed_path, "r", encoding="utf-8") as f:
        seed_platforms = json.load(f)

    index, manifests = convert(seed_platforms)

    write_json(os.path.join(repo_root, "index.json"), index)
    for filename, manifest in manifests.items():
        write_json(os.path.join(repo_root, filename), manifest)

    print(f"Wrote index.json with {len(index['platformList'])} entries")
    print(f"Wrote {len(manifests)} manifest files under platforms/")


if __name__ == "__main__":
    main()
