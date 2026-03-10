#!/usr/bin/env python3
"""
detect_duplicates.py
--------------------
Concrete duplicate detection engine for Tax Receipt Autopilot.

Algorithm:
  Two transactions are considered duplicates if ALL of:
    1. Vendor similarity >= VENDOR_THRESHOLD (fuzzy match)
    2. Amount difference <= AMOUNT_TOLERANCE
    3. Date difference <= DATE_WINDOW_DAYS

Merge strategy: keep the record with a receipt; if both or neither
have receipts, keep the one with more fields populated.

Usage:
    python3 detect_duplicates.py <transactions.json> [--output <merged.json>]

Input: JSON array of transaction dicts (from parse_bank_statement.py or ledger export)
Output: JSON with keys:
    "clean":      list of deduplicated transactions
    "duplicates": list of {kept, merged, reason} groups
    "stats":      summary counts
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from thefuzz import fuzz
except ImportError:
    try:
        from fuzzywuzzy import fuzz  # legacy fallback
    except ImportError:
        # Fallback: simple Jaccard set similarity — less accurate than thefuzz.
        # Vendor names like "AMZN MKTP" vs "Amazon" will score 0 instead of ~80.
        print(
            "WARNING: thefuzz not installed — using basic vendor matching (less accurate).\n"
            "         Duplicate detection may miss variants like 'AMZN MKTP' vs 'Amazon'.\n"
            "         Install for best results: pip install thefuzz",
            file=sys.stderr,
        )
        class fuzz:
            @staticmethod
            def token_sort_ratio(a, b):
                a_words = set(a.lower().split())
                b_words = set(b.lower().split())
                if not a_words or not b_words:
                    return 0
                intersection = a_words & b_words
                union = a_words | b_words
                return int(100 * len(intersection) / len(union))


# ---------------------------------------------------------------------------
# Thresholds — adjust these to tune sensitivity
# ---------------------------------------------------------------------------
VENDOR_THRESHOLD    = 80    # Fuzzy match score 0-100; 80 = high similarity required
AMOUNT_TOLERANCE    = 0.02  # Max $ difference to still consider duplicate ($0.02)
DATE_WINDOW_DAYS    = 3     # Max calendar days apart to consider duplicate
RECURRING_WINDOW    = 35    # Days window for recurring charge detection (25–35 day range)
RECURRING_AMOUNT_T  = 0.01  # Recurring charges must match to the penny (mostly)


def parse_date(date_str: str) -> datetime | None:
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def field_count(tx: dict) -> int:
    """Count non-empty, non-None fields — used for merge priority."""
    return sum(1 for v in tx.values() if v is not None and v != "" and v is not False)


def is_duplicate(tx1: dict, tx2: dict) -> tuple[bool, str]:
    """
    Returns (is_dup: bool, reason: str).
    """
    # --- 1. Vendor similarity ---
    v1 = str(tx1.get("vendor", "")).strip()
    v2 = str(tx2.get("vendor", "")).strip()
    if not v1 or not v2:
        return False, ""
    vendor_score = fuzz.token_sort_ratio(v1, v2)
    if vendor_score < VENDOR_THRESHOLD:
        return False, ""

    # --- 2. Amount match ---
    try:
        a1 = float(tx1.get("amount", 0))
        a2 = float(tx2.get("amount", 0))
    except (TypeError, ValueError):
        return False, ""
    if abs(a1 - a2) > AMOUNT_TOLERANCE:
        return False, ""

    # --- 3. Date proximity ---
    d1 = parse_date(str(tx1.get("transaction_date", "")))
    d2 = parse_date(str(tx2.get("transaction_date", "")))
    if not d1 or not d2:
        return False, ""
    date_diff = abs((d1 - d2).days)
    if date_diff > DATE_WINDOW_DAYS:
        return False, ""

    reason = (
        f"Vendor match: {vendor_score}% | "
        f"Amount: ${a1:.2f} vs ${a2:.2f} | "
        f"Date diff: {date_diff} days"
    )
    return True, reason


def merge_pair(tx1: dict, tx2: dict, reason: str) -> dict:
    """
    Merge two duplicate transactions into one, keeping the best data.
    Priority:
      1. The record with receipt_matched=True
      2. The record with source='Email Receipt' (most structured)
      3. The record with more fields populated
    """
    def priority(tx):
        score = 0
        if tx.get("receipt_matched"):               score += 100
        if tx.get("source") == "Email Receipt":     score += 10
        if tx.get("category"):                      score += 5
        score += field_count(tx)
        return score

    winner, loser = (tx1, tx2) if priority(tx1) >= priority(tx2) else (tx2, tx1)
    merged = dict(winner)

    # Pull in any non-empty fields from loser that winner is missing
    for k, v in loser.items():
        if k == "notes":
            continue
        if (merged.get(k) is None or merged.get(k) == "") and v:
            merged[k] = v

    # Combine notes
    notes_parts = []
    if winner.get("notes"):
        notes_parts.append(winner["notes"])
    if loser.get("notes"):
        notes_parts.append(loser["notes"])
    notes_parts.append(f"[AUTO-MERGED duplicate: {reason}]")
    if loser.get("source"):
        notes_parts.append(f"[Duplicate source: {loser['source']}]")
    merged["notes"] = " | ".join(notes_parts)

    return merged


def detect_recurring(transactions: list[dict]) -> list[dict]:
    """
    Flag recurring charges (same vendor, same amount, ~monthly).
    Does NOT merge these — they're legitimate repeat charges.
    """
    # Group by vendor + amount
    groups: dict[str, list[dict]] = {}
    for tx in transactions:
        key = f"{tx.get('vendor','').lower().strip()}::{tx.get('amount', 0)}"
        groups.setdefault(key, []).append(tx)

    for key, group in groups.items():
        if len(group) >= 2:
            # Check if dates are roughly monthly apart
            dates = sorted([parse_date(str(t.get("transaction_date","")))
                            for t in group if parse_date(str(t.get("transaction_date","")))])
            for i in range(1, len(dates)):
                diff = (dates[i] - dates[i-1]).days
                if 25 <= diff <= 35:
                    for tx in group:
                        tx["_recurring"] = True
                    break

    return transactions


def run_detection(transactions: list[dict]) -> dict:
    """
    Main dedup loop. O(n²) — acceptable for typical ledger sizes (<10,000 txns).
    For very large imports, pre-filter the input to a specific date range before running.
    """
    n = len(transactions)
    used = [False] * n
    clean = []
    duplicate_groups = []

    for i in range(n):
        if used[i]:
            continue
        current = transactions[i]
        dupes_of_i = []

        for j in range(i + 1, n):
            if used[j]:
                continue
            is_dup, reason = is_duplicate(current, transactions[j])
            if is_dup:
                dupes_of_i.append((j, reason))

        if dupes_of_i:
            # Merge all duplicates into current
            merged = current
            merged_sources = [current]
            for j, reason in dupes_of_i:
                merged = merge_pair(merged, transactions[j], reason)
                merged_sources.append(transactions[j])
                used[j] = True

            clean.append(merged)
            duplicate_groups.append({
                "kept":    merged,
                "merged":  [transactions[j] for j, _ in dupes_of_i],
                "reasons": [r for _, r in dupes_of_i],
            })
        else:
            clean.append(current)

        used[i] = True

    # Flag recurring after dedup, then strip the internal key before returning.
    # We count recurring charges for stats but do NOT leave _recurring on the
    # transaction dicts — strip it before writing back to ledger.json.
    clean = detect_recurring(clean)
    recurring_count = sum(1 for t in clean if t.get("_recurring"))
    for tx in clean:
        tx.pop("_recurring", None)

    return {
        "clean": clean,
        "duplicates": duplicate_groups,
        "stats": {
            "input_count":          n,
            "output_count":         len(clean),
            "duplicates_merged":    n - len(clean),
            "duplicate_groups":     len(duplicate_groups),
            "recurring_flagged":    recurring_count,
        }
    }


def main():
    ap = argparse.ArgumentParser(description="Detect and merge duplicate transactions")
    ap.add_argument("input",   help="Input JSON file (array of transaction dicts)")
    ap.add_argument("--output", help="Output JSON file (default: stdout)")
    ap.add_argument("--vendor-threshold", type=int, default=VENDOR_THRESHOLD,
                    help=f"Fuzzy vendor match threshold 0-100 (default: {VENDOR_THRESHOLD})")
    ap.add_argument("--date-window", type=int, default=DATE_WINDOW_DAYS,
                    help=f"Max days between duplicate dates (default: {DATE_WINDOW_DAYS})")
    args = ap.parse_args()

    with open(args.input) as f:
        transactions = json.load(f)

    if not isinstance(transactions, list):
        print("ERROR: Input must be a JSON array of transactions", file=sys.stderr)
        sys.exit(1)

    result = run_detection(transactions)

    output = json.dumps(result, indent=2, default=str)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        stats = result["stats"]
        print(f"✅ Dedup complete:", file=sys.stderr)
        print(f"   Input:    {stats['input_count']} transactions", file=sys.stderr)
        print(f"   Output:   {stats['output_count']} transactions", file=sys.stderr)
        print(f"   Merged:   {stats['duplicates_merged']} duplicates removed", file=sys.stderr)
        print(f"   Recurring:{stats['recurring_flagged']} recurring charges flagged", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()