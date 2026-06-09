import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_compair.cli import main
from hermes_compair.inventory import inventory_folder


class InventoryTests(unittest.TestCase):
    def test_inventory_scans_files_and_returns_document_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc_path = root / "notes" / "meeting.md"
            doc_path.parent.mkdir()
            doc_path.write_text("Synthetic meeting notes.\n", encoding="utf-8")

            records = inventory_folder(root)

            self.assertEqual(len(records), 1)
            record = records[0]
            expected_hash = hashlib.sha256(doc_path.read_bytes()).hexdigest()
            self.assertEqual(record.source_path, str(doc_path))
            self.assertEqual(record.title, "meeting.md")
            self.assertEqual(record.content_hash, expected_hash)
            self.assertEqual(record.document_type, "markdown")
            self.assertEqual(record.metadata["extension"], ".md")
            self.assertEqual(record.metadata["size_bytes"], len(doc_path.read_bytes()))
            self.assertEqual(record.source_system, "local_file")
            self.assertTrue(record.document_id.startswith("sha256:"))
            json.dumps(record.to_dict())

    def test_inventory_skips_git_hidden_cache_and_database_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            keep = root / "visible.txt"
            keep.write_text("Synthetic visible content.\n", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("ignored", encoding="utf-8")
            (root / ".hidden").mkdir()
            (root / ".hidden" / "secret.txt").write_text("ignored", encoding="utf-8")
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "module.pyc").write_bytes(b"ignored")
            (root / ".pytest_cache").mkdir()
            (root / ".pytest_cache" / "state").write_text("ignored", encoding="utf-8")
            (root / "project.sqlite").write_text("ignored", encoding="utf-8")
            (root / "local.db").write_text("ignored", encoding="utf-8")
            for filename in (
                "project.sqlite-wal",
                "project.sqlite-shm",
                "project.sqlite-journal",
                "project.sqlite3-wal",
                "project.sqlite3-shm",
                "project.sqlite3-journal",
                "local.db-journal",
            ):
                (root / filename).write_text("ignored", encoding="utf-8")

            records = inventory_folder(root)

            self.assertEqual([Path(record.source_path).name for record in records], ["visible.txt"])
            self.assertEqual(records[0].document_type, "text")

    def test_inventory_skips_plain_cache_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            keep = root / "visible.txt"
            keep.write_text("Synthetic visible content.\n", encoding="utf-8")
            (root / "cache").mkdir()
            (root / "cache" / "cached.txt").write_text("ignored", encoding="utf-8")

            records = inventory_folder(root)

            self.assertEqual([Path(record.source_path).name for record in records], ["visible.txt"])

    def test_inventory_skips_hidden_files_at_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            keep = root / "visible.txt"
            keep.write_text("Synthetic visible content.\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=ignored\n", encoding="utf-8")

            records = inventory_folder(root)

            self.assertEqual([Path(record.source_path).name for record in records], ["visible.txt"])

    def test_inventory_skips_symlinked_files_that_escape_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "scan"
            root.mkdir()
            keep = root / "visible.txt"
            keep.write_text("Synthetic visible content.\n", encoding="utf-8")
            outside = base / "outside-secret.txt"
            outside.write_text("ignored", encoding="utf-8")
            (root / "linked-secret.txt").symlink_to(outside)

            records = inventory_folder(root)

            self.assertEqual([Path(record.source_path).name for record in records], ["visible.txt"])

    def test_inventory_rejects_symlinked_root_with_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "scan"
            root.mkdir()
            (root / "visible.txt").write_text("Synthetic visible content.\n", encoding="utf-8")
            linked_root = base / "linked-scan"
            linked_root.symlink_to(root, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "Inventory folder must not be a symlink"):
                inventory_folder(linked_root)

    def test_inventory_rejects_missing_folder_with_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing"

            with self.assertRaisesRegex(FileNotFoundError, "Inventory folder not found"):
                inventory_folder(missing)

    def test_cli_inventory_json_outputs_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "contract.txt").write_text("Synthetic contract excerpt.\n", encoding="utf-8")

            with patch("sys.stdout") as stdout:
                code = main(["inventory", str(root), "--json"])

            self.assertEqual(code, 0)
            payload = json.loads("".join(call.args[0] for call in stdout.write.call_args_list))
            self.assertEqual(len(payload["documents"]), 1)
            self.assertEqual(payload["documents"][0]["document_type"], "text")
            self.assertIn("content_hash", payload["documents"][0])

    def test_cli_inventory_missing_folder_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing"

            with patch("sys.stderr") as stderr:
                code = main(["inventory", str(missing), "--json"])

            self.assertEqual(code, 2)
            self.assertIn(
                "Inventory folder not found",
                "".join(call.args[0] for call in stderr.write.call_args_list),
            )


if __name__ == "__main__":
    unittest.main()
