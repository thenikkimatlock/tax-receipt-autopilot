#!/usr/bin/env python3
"""
backup_ledger.py
----------------
Creates a timestamped backup of your Tax Receipt Autopilot ledger (and optional
vendors file) in a backups/ subfolder next to the source files.

Usage:
    python3 backup_ledger.py <ledger.json>
    python3 backup_ledger.py <ledger.json> --vendors <vendors.json>
    python3 backup_ledger.py <ledger.json> --output-dir <path>

Output:
    <output_dir>/ledger-backup-YYYYMMDD-HHMMSS.json
    <output_dir>/vendors-backup-YYYYMMDD-HHMMSS.json  (if --vendors provided)

Default output directory: <ledger_dir>/backups/
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 output on Windows (avoids cp1252 crash on → and other non-ASCII chars)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]


def backup_file(source: Path, output_dir: Path, label: str) -> Path:
    """Copy source to output_dir with a timestamped filename. Returns destination path."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = label
    dest = output_dir / f"{stem}-backup-{timestamp}{source.suffix}"
    shutil.copy2(source, dest)
    return dest


def validate_json(path: Path) -> bool:
    """Quick sanity check — confirm the file is valid JSON before backing up."""
    try:
        with open(path, encoding="utf-8") as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, OSError):
        return False


def prune_old_backups(output_dir: Path, label: str, keep: int) -> int:
    """Remove oldest backups beyond the keep limit. Returns count removed."""
    pattern = f"{label}-backup-*.json"
    backups = sorted(output_dir.glob(pattern))
    to_remove = backups[: max(0, len(backups) - keep)]
    for f in to_remove:
        f.unlink()
    return len(to_remove)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Create a timestamped backup of your Tax Receipt Autopilot ledger"
    )
    ap.add_argument("ledger", help="Path to ledger.json")
    ap.add_argument("--vendors", default="", help="Path to vendors.json (optional)")
    ap.add_argument(
        "--output-dir",
        dest="output_dir",
        default="",
        help="Directory to write backups into (default: <ledger_dir>/backups/)",
    )
    ap.add_argument(
        "--keep",
        type=int,
        default=30,
        help="Max number of backups to keep per file (default: 30, oldest removed first)",
    )
    args = ap.parse_args()

    ledger_path = Path(args.ledger).expanduser().resolve()
    if not ledger_path.exists():
        print(f"ERROR: Ledger not found: {ledger_path}", file=sys.stderr)
        sys.exit(1)

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
    else:
        output_dir = ledger_path.parent / "backups"

    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    # Back up ledger
    if not validate_json(ledger_path):
        print(
            f"WARNING: {ledger_path.name} does not appear to be valid JSON. "
            "Backing up anyway — check the file for corruption.",
            file=sys.stderr,
        )
    dest = backup_file(ledger_path, output_dir, "ledger")
    removed = prune_old_backups(output_dir, "ledger", args.keep)
    results.append({"file": "ledger", "dest": dest, "pruned": removed})

    # Back up vendors (optional)
    if args.vendors:
        vendors_path = Path(args.vendors).expanduser().resolve()
        if not vendors_path.exists():
            print(
                f"WARNING: Vendors file not found: {vendors_path} — skipping.",
                file=sys.stderr,
            )
        else:
            if not validate_json(vendors_path):
                print(
                    f"WARNING: {vendors_path.name} does not appear to be valid JSON. "
                    "Backing up anyway.",
                    file=sys.stderr,
                )
            dest_v = backup_file(vendors_path, output_dir, "vendors")
            removed_v = prune_old_backups(output_dir, "vendors", args.keep)
            results.append({"file": "vendors", "dest": dest_v, "pruned": removed_v})

    # Summary
    print(f"\nBackup complete — {output_dir}")
    print("-" * 45)
    for r in results:
        print(f"  {r['file']:10s}  →  {r['dest'].name}")
        if r["pruned"]:
            print(f"             (pruned {r['pruned']} old backup(s), keeping {args.keep})")
    print()


if __name__ == "__main__":
    main()
