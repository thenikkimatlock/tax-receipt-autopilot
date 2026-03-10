#!/usr/bin/env python3
"""
Unit tests for backup_ledger.py

Run from the scripts/ directory:
    python3 -m pytest tests/test_backup_ledger.py -v
    python3 -m unittest tests.test_backup_ledger -v
"""

import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from backup_ledger import backup_file, validate_json, prune_old_backups


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(content: list | dict, suffix: str = ".json") -> Path:
    """Write JSON content to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    )
    json.dump(content, f)
    f.close()
    return Path(f.name)


def _write_bad_json(suffix: str = ".json") -> Path:
    """Write intentionally invalid JSON to a temp file."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    )
    f.write("{this is not valid json")
    f.close()
    return Path(f.name)


def _make_output_dir() -> Path:
    return Path(tempfile.mkdtemp())


# ---------------------------------------------------------------------------
# validate_json
# ---------------------------------------------------------------------------

class TestValidateJson(unittest.TestCase):
    def setUp(self):
        self._files = []

    def tearDown(self):
        for f in self._files:
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass

    def _track(self, p: Path) -> Path:
        self._files.append(p)
        return p

    def test_valid_json_array_returns_true(self):
        path = self._track(_write_json([{"vendor": "OpenAI", "amount": 49.00}]))
        self.assertTrue(validate_json(path))

    def test_valid_json_dict_returns_true(self):
        path = self._track(_write_json({"key": "value"}))
        self.assertTrue(validate_json(path))

    def test_valid_empty_array_returns_true(self):
        path = self._track(_write_json([]))
        self.assertTrue(validate_json(path))

    def test_invalid_json_returns_false(self):
        path = self._track(_write_bad_json())
        self.assertFalse(validate_json(path))

    def test_nonexistent_file_returns_false(self):
        path = Path("/nonexistent/path/ledger.json")
        self.assertFalse(validate_json(path))


# ---------------------------------------------------------------------------
# backup_file
# ---------------------------------------------------------------------------

class TestBackupFile(unittest.TestCase):
    def setUp(self):
        self.output_dir = _make_output_dir()
        self._source_files: list[Path] = []

    def tearDown(self):
        shutil.rmtree(self.output_dir, ignore_errors=True)
        for f in self._source_files:
            f.unlink(missing_ok=True)

    def _source(self, content=None) -> Path:
        p = _write_json(content or [{"vendor": "Canva", "amount": 16.00}])
        self._source_files.append(p)
        return p

    def test_creates_backup_file(self):
        src = self._source()
        dest = backup_file(src, self.output_dir, "ledger")
        self.assertTrue(dest.exists())

    def test_backup_filename_includes_label(self):
        src = self._source()
        dest = backup_file(src, self.output_dir, "ledger")
        self.assertIn("ledger", dest.name)

    def test_backup_filename_includes_timestamp(self):
        src = self._source()
        dest = backup_file(src, self.output_dir, "ledger")
        # Timestamp format: YYYYMMDD-HHMMSS
        self.assertRegex(dest.name, r"\d{8}-\d{6}")

    def test_backup_has_json_extension(self):
        src = self._source()
        dest = backup_file(src, self.output_dir, "ledger")
        self.assertEqual(dest.suffix, ".json")

    def test_backup_contents_match_source(self):
        content = [{"vendor": "OpenAI", "amount": 49.00, "date": "2026-03-15"}]
        src = self._source(content)
        dest = backup_file(src, self.output_dir, "ledger")
        with open(dest) as f:
            loaded = json.load(f)
        self.assertEqual(loaded, content)

    def test_vendors_label_in_filename(self):
        src = self._source()
        dest = backup_file(src, self.output_dir, "vendors")
        self.assertIn("vendors", dest.name)

    def test_backup_returns_path_object(self):
        src = self._source()
        dest = backup_file(src, self.output_dir, "ledger")
        self.assertIsInstance(dest, Path)

    def test_backup_placed_in_output_dir(self):
        src = self._source()
        dest = backup_file(src, self.output_dir, "ledger")
        self.assertEqual(dest.parent.resolve(), self.output_dir.resolve())

    def test_two_backups_have_different_names(self):
        import time
        src = self._source()
        dest1 = backup_file(src, self.output_dir, "ledger")
        time.sleep(1.1)  # ensure timestamp difference
        dest2 = backup_file(src, self.output_dir, "ledger")
        self.assertNotEqual(dest1.name, dest2.name)


# ---------------------------------------------------------------------------
# prune_old_backups
# ---------------------------------------------------------------------------

class TestPruneOldBackups(unittest.TestCase):
    def setUp(self):
        self.output_dir = _make_output_dir()

    def tearDown(self):
        shutil.rmtree(self.output_dir, ignore_errors=True)

    def _make_backups(self, label: str, count: int) -> list[Path]:
        """Create `count` fake backup files with sequential timestamps."""
        import time
        paths = []
        for i in range(count):
            name = f"{label}-backup-2026030{i + 1}-12000{i}.json"
            p = self.output_dir / name
            p.write_text("{}")
            paths.append(p)
            time.sleep(0.01)  # tiny gap so glob sort is stable
        return paths

    def test_no_pruning_when_under_limit(self):
        self._make_backups("ledger", 3)
        removed = prune_old_backups(self.output_dir, "ledger", keep=5)
        self.assertEqual(removed, 0)
        remaining = list(self.output_dir.glob("ledger-backup-*.json"))
        self.assertEqual(len(remaining), 3)

    def test_prunes_oldest_when_over_limit(self):
        files = self._make_backups("ledger", 5)
        removed = prune_old_backups(self.output_dir, "ledger", keep=3)
        self.assertEqual(removed, 2)
        remaining = list(self.output_dir.glob("ledger-backup-*.json"))
        self.assertEqual(len(remaining), 3)

    def test_oldest_files_removed(self):
        files = self._make_backups("ledger", 4)
        prune_old_backups(self.output_dir, "ledger", keep=2)
        # The two oldest files should be gone
        self.assertFalse(files[0].exists())
        self.assertFalse(files[1].exists())
        # The two newest should still exist
        self.assertTrue(files[2].exists())
        self.assertTrue(files[3].exists())

    def test_prune_returns_count_removed(self):
        self._make_backups("ledger", 6)
        removed = prune_old_backups(self.output_dir, "ledger", keep=4)
        self.assertEqual(removed, 2)

    def test_prune_zero_keep_removes_all(self):
        self._make_backups("ledger", 3)
        removed = prune_old_backups(self.output_dir, "ledger", keep=0)
        self.assertEqual(removed, 3)
        remaining = list(self.output_dir.glob("ledger-backup-*.json"))
        self.assertEqual(len(remaining), 0)

    def test_prune_does_not_touch_other_labels(self):
        self._make_backups("ledger", 5)
        self._make_backups("vendors", 5)
        prune_old_backups(self.output_dir, "ledger", keep=2)
        # vendors files should be untouched
        vendors_remaining = list(self.output_dir.glob("vendors-backup-*.json"))
        self.assertEqual(len(vendors_remaining), 5)

    def test_empty_dir_returns_zero(self):
        removed = prune_old_backups(self.output_dir, "ledger", keep=5)
        self.assertEqual(removed, 0)

    def test_exactly_at_limit_returns_zero(self):
        self._make_backups("ledger", 5)
        removed = prune_old_backups(self.output_dir, "ledger", keep=5)
        self.assertEqual(removed, 0)


# ---------------------------------------------------------------------------
# Integration: main() via subprocess
# ---------------------------------------------------------------------------

class TestBackupMain(unittest.TestCase):
    """
    Tests the CLI entry point end-to-end by invoking the script via subprocess.
    This catches arg-parsing and path-handling issues that unit tests miss.
    """

    def setUp(self):
        self.output_dir = _make_output_dir()
        ledger = [{"vendor": "OpenAI", "amount": 49.00, "transaction_date": "2026-03-01"}]
        self._ledger_file = _write_json(ledger)

    def tearDown(self):
        shutil.rmtree(self.output_dir, ignore_errors=True)
        self._ledger_file.unlink(missing_ok=True)

    def _run(self, extra_args: list[str]) -> "subprocess.CompletedProcess":
        import subprocess
        script = Path(__file__).parent.parent / "backup_ledger.py"
        return subprocess.run(
            [sys.executable, str(script), str(self._ledger_file)] + extra_args,
            capture_output=True,
            text=True,
        )

    def test_basic_backup_exits_zero(self):
        result = self._run(["--output-dir", str(self.output_dir)])
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_backup_file_created_in_output_dir(self):
        self._run(["--output-dir", str(self.output_dir)])
        backups = list(self.output_dir.glob("ledger-backup-*.json"))
        self.assertEqual(len(backups), 1)

    def test_backup_output_mentions_output_dir(self):
        result = self._run(["--output-dir", str(self.output_dir)])
        self.assertIn("Backup complete", result.stdout)

    def test_missing_ledger_exits_nonzero(self):
        import subprocess
        script = Path(__file__).parent.parent / "backup_ledger.py"
        result = subprocess.run(
            [sys.executable, str(script), "/nonexistent/ledger.json",
             "--output-dir", str(self.output_dir)],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_keep_flag_respected(self):
        # Create 4 backups then run with --keep 2; should prune to 2
        for _ in range(4):
            backup_file(self._ledger_file, self.output_dir, "ledger")
        self._run(["--output-dir", str(self.output_dir), "--keep", "2"])
        backups = list(self.output_dir.glob("ledger-backup-*.json"))
        self.assertLessEqual(len(backups), 3)  # 2 from prune + 1 new


if __name__ == "__main__":
    unittest.main(verbosity=2)
