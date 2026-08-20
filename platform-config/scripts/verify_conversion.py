#!/usr/bin/env python3
"""Verify the generated index.json + platforms/*.json against the source
platforms_seed.json: content equivalence AND schema validity.

Usage:
    python3 scripts/verify_conversion.py [path-to-platforms_seed.json]

Defaults to scripts/platforms_seed.json (the committed input copy) if no
path is given. Must be run from the repo root (or any cwd — paths are
resolved relative to this script's location).

Checks, for every one of the 120 platforms:
  1. name, shortname/shortName, and both acceptedFilenameRegex values
     (platform-level and every player-level) match the seed exactly.
  2. Player list order matches the seed's order, not just membership/count.
  3. The six non-nullable DaijishoJson.kt fields (platform.name,
     platform.uniqueId, platform.shortname, and per-player name/uniqueId/
     amStartArguments) are present and non-null/non-empty in every one of
     the 121 generated files (index.json + 120 manifests).
  4. index.json has exactly 120 entries; exactly 120 files exist under
     platforms/; every filename in the index resolves to a file that
     actually exists on disk.
  5. revisionNumber is 1 (never 0) in every index entry and every manifest.
  6. An empty playerList (the elektor case) is accepted as valid.
"""

import json
import os
import sys

EXPECTED_COUNT = 120


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)

    if len(sys.argv) > 1:
        seed_path = sys.argv[1]
    else:
        seed_path = os.path.join(script_dir, "platforms_seed.json")

    seed_platforms = load_json(seed_path)
    seed_by_id = {p["id"]: p for p in seed_platforms}

    errors = []
    warnings = []

    # --- Check 4a: seed sanity ---
    if len(seed_platforms) != EXPECTED_COUNT:
        errors.append(f"Seed has {len(seed_platforms)} platforms, expected {EXPECTED_COUNT}")

    # --- Load index.json ---
    index_path = os.path.join(repo_root, "index.json")
    index = load_json(index_path)

    if "baseUri" not in index:
        errors.append("index.json missing baseUri")

    platform_list = index.get("platformList", [])

    # --- Check 4b: index has exactly 120 entries ---
    if len(platform_list) != EXPECTED_COUNT:
        errors.append(f"index.json has {len(platform_list)} entries, expected {EXPECTED_COUNT}")

    # --- Check 4c: exactly 120 files exist under platforms/ ---
    platforms_dir = os.path.join(repo_root, "platforms")
    on_disk_files = sorted(f for f in os.listdir(platforms_dir) if f.endswith(".json"))
    if len(on_disk_files) != EXPECTED_COUNT:
        errors.append(f"platforms/ has {len(on_disk_files)} .json files, expected {EXPECTED_COUNT}")

    matched_count = 0
    field_diff_count = 0
    nonnull_violation_count = 0
    revision_violation_count = 0
    elektor_checked = False

    seen_ids = set()

    for entry in platform_list:
        uid = entry.get("platformUniqueId")
        filename = entry.get("filename")
        seen_ids.add(uid)

        # --- Check 4d: filename resolves to an existing file ---
        manifest_path = os.path.join(repo_root, filename) if filename else None
        if not filename or not os.path.isfile(manifest_path):
            errors.append(f"[{uid}] index filename '{filename}' does not resolve to an existing file")
            continue

        # --- Check 5 (index side): revisionNumber == 1 ---
        if entry.get("revisionNumber") != 1:
            revision_violation_count += 1
            errors.append(f"[{uid}] index revisionNumber is {entry.get('revisionNumber')!r}, expected 1")

        seed = seed_by_id.get(uid)
        if seed is None:
            errors.append(f"[{uid}] present in index.json but not found in seed")
            continue

        manifest = load_json(manifest_path)

        # --- Check 5 (manifest side): revisionNumber == 1 ---
        if manifest.get("revisionNumber") != 1:
            revision_violation_count += 1
            errors.append(f"[{uid}] manifest revisionNumber is {manifest.get('revisionNumber')!r}, expected 1")

        platform = manifest.get("platform", {})

        # --- Check 3: non-nullable platform fields ---
        for field in ("name", "uniqueId", "shortname"):
            val = platform.get(field)
            if val is None or (isinstance(val, str) and val == ""):
                nonnull_violation_count += 1
                errors.append(f"[{uid}] platform.{field} is null/empty (non-nullable field)")

        # --- Check 1: field equivalence (platform-level) ---
        local_diffs = []
        if platform.get("name") != seed.get("name"):
            local_diffs.append("name")
        if platform.get("shortname") != seed.get("shortName"):
            local_diffs.append("shortname")
        if platform.get("acceptedFilenameRegex") != seed.get("acceptedFilenameRegex"):
            local_diffs.append("acceptedFilenameRegex")
        if platform.get("uniqueId") != seed.get("id"):
            local_diffs.append("uniqueId")

        player_list = manifest.get("playerList", [])
        seed_players = seed.get("players", [])

        # --- Check 6: elektor empty playerList accepted ---
        if uid == "elektor":
            elektor_checked = True
            if len(seed_players) != 0:
                warnings.append("elektor seed unexpectedly has players — edge-case assumption changed")
            if len(player_list) != 0:
                local_diffs.append("playerList (expected empty for elektor)")

        # --- Check 2: player list order + membership ---
        if len(player_list) != len(seed_players):
            local_diffs.append(f"playerList length ({len(player_list)} vs seed {len(seed_players)})")
        else:
            for i, (mp, sp) in enumerate(zip(player_list, seed_players)):
                if mp.get("name") != sp.get("name"):
                    local_diffs.append(f"playerList[{i}].name")
                if mp.get("uniqueId") != sp.get("uniqueId"):
                    local_diffs.append(f"playerList[{i}].uniqueId")
                if mp.get("amStartArguments") != sp.get("amStartArguments"):
                    local_diffs.append(f"playerList[{i}].amStartArguments")
                if mp.get("acceptedFilenameRegex") != sp.get("acceptedFilenameRegex"):
                    local_diffs.append(f"playerList[{i}].acceptedFilenameRegex")

                # --- Check 3: non-nullable player fields ---
                for field in ("name", "uniqueId", "amStartArguments"):
                    val = mp.get(field)
                    if val is None or (isinstance(val, str) and val == ""):
                        nonnull_violation_count += 1
                        errors.append(f"[{uid}] playerList[{i}].{field} is null/empty (non-nullable field)")

        if local_diffs:
            field_diff_count += 1
            errors.append(f"[{uid}] field diffs: {local_diffs}")
        else:
            matched_count += 1

    # --- presence check for uniqueIds that must never be renamed/removed ---
    for must_have in ("arcade", "model3", "triforce", "idtech"):
        if must_have not in seen_ids:
            errors.append(f"required uniqueId '{must_have}' missing from index.json")

    # --- ids present in seed but missing from index ---
    missing_from_index = set(seed_by_id.keys()) - seen_ids
    if missing_from_index:
        errors.append(f"ids in seed but missing from index.json: {sorted(missing_from_index)}")

    if not elektor_checked:
        errors.append("elektor platform not found in index.json — could not verify empty playerList edge case")

    print("=== Verification summary ===")
    print(f"Seed platforms:          {len(seed_platforms)}")
    print(f"Index entries:           {len(platform_list)}")
    print(f"Manifest files on disk:  {len(on_disk_files)}")
    print(f"Matched (0 field diffs): {matched_count}/{EXPECTED_COUNT}")
    print(f"Platforms with field diffs: {field_diff_count}")
    print(f"Non-null constraint violations: {nonnull_violation_count}")
    print(f"revisionNumber violations: {revision_violation_count}")
    print(f"elektor empty-playerList edge case checked: {elektor_checked}")
    print(f"required uniqueIds present (arcade/model3/triforce/idtech): "
          f"{all(x in seen_ids for x in ('arcade', 'model3', 'triforce', 'idtech'))}")

    if warnings:
        print("\n=== Warnings ===")
        for w in warnings:
            print(f"  WARN: {w}")

    if errors:
        print(f"\n=== FAILED: {len(errors)} error(s) ===")
        for e in errors:
            print(f"  ERROR: {e}")
        return 1

    print("\n=== PASSED: all checks green ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
