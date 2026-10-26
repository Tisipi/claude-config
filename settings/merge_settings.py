#!/usr/bin/env python3
# ABOUTME: Merges the shared Claude Code settings (settings.shared.json) into the user's settings.json.
# Additive and idempotent: lists are unioned, objects merged recursively, existing scalar values win.
# Nothing the user already has is ever removed or overridden.

import argparse
import copy
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

DEFAULT_TARGET = Path.home() / ".claude" / "settings.json"
DEFAULT_SHARED = Path(__file__).with_name("settings.shared.json")
JSON_INDENT = 2
BACKUP_SUFFIX = ".bak"


def merge(shared, existing):
    """Return `existing` extended with everything in `shared`; neither argument is modified."""
    if isinstance(shared, dict) and isinstance(existing, dict):
        merged = copy.deepcopy(existing)
        for key, value in shared.items():
            merged[key] = merge(value, merged[key]) if key in merged else copy.deepcopy(value)
        return merged
    if isinstance(shared, list) and isinstance(existing, list):
        merged = copy.deepcopy(existing)
        merged.extend(copy.deepcopy(item) for item in shared if item not in existing)
        return merged
    return copy.deepcopy(existing)


def merge_files(shared_path, target_path, dry_run=False):
    """Merge the shared settings into the target file. Returns True when the target changes (or would)."""
    shared = _read_json(Path(shared_path))
    target = Path(os.path.realpath(target_path))
    existing = _read_json(target) if target.exists() else {}

    merged = merge(shared, existing)
    if merged == existing and target.exists():
        return False
    if dry_run:
        return True

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.copy2(target, target.with_name(target.name + BACKUP_SUFFIX))
    _write_json_atomically(target, merged)
    return True


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path} is not valid JSON: {error}") from error


def _write_json_atomically(path, data):
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=path.name, suffix=".tmp", delete=False
    ) as handle:
        json.dump(data, handle, indent=JSON_INDENT)
        handle.write("\n")
    os.replace(handle.name, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Merge shared Claude Code settings into settings.json.")
    parser.add_argument("--shared", type=Path, default=DEFAULT_SHARED)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--dry-run", action="store_true", help="report whether a change is needed, write nothing")
    args = parser.parse_args(argv)

    existed = args.target.exists()
    try:
        changed = merge_files(args.shared, args.target, dry_run=args.dry_run)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if not changed:
        print(f"{args.target} is already up to date")
    elif args.dry_run:
        print(f"{args.target} would be {'updated' if existed else 'created'}")
    elif existed:
        print(f"{args.target} updated (previous version saved as {args.target.name}{BACKUP_SUFFIX})")
    else:
        print(f"{args.target} created")
    return 0


if __name__ == "__main__":
    sys.exit(main())
