"""Exercise checksum recognition with actual Git objects and ZIP byte failures."""

import hashlib
import json
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

import test_auto_code_review as workflow_tests


class PreservationChecksumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workflow_tests.InlineWorkflowTests.setUpClass()

    def setUp(self):
        self.harness = workflow_tests.InlineWorkflowTests()
        self.harness.setUp()
        self.addCleanup(self.harness.doCleanups)
        self.caller = self.harness.caller
        self.git("init", "--initial-branch=master")
        (self.caller / "base.txt").write_text("Original source checkout.\n")
        self.commit()
        self.original_head = self.git("rev-parse", "HEAD").strip()
        self.capsule = self.caller / "migration-preservation/TESTHOST/20261004T083909Z"
        self.capsule.mkdir(parents=True)
        self.manifest_path = self.capsule / "PRESERVATION.json"
        self.archive_path = self.capsule / "source-001.zip"
        self.source_path = "worktrees/fixture/source.py"
        self.source_bytes = b"print('preserved source')\n"
        self.source_manifest = {
            "files": [
                {
                    "source": r"C:\fixture\repo\source.py",
                    "archive_path": self.source_path,
                    "bytes": len(self.source_bytes),
                    "sha256": hashlib.sha256(self.source_bytes).hexdigest(),
                    "status": "??",
                    "original_head": self.original_head,
                    "original_branch": "master",
                    "scanner": "screened source bytes",
                }
            ],
            "note": "Exact source bytes; no execution.",
        }
        self.manifest = {
            "source_repo": "test/fixture",
            "machine": "TESTHOST",
            "created_utc": "2026-10-04T08:39:29.566835+00:00",
            "archives": [{}],
            "source_checkouts": [
                {
                    "path": r"C:\fixture\repo",
                    "head": self.original_head,
                    "branch": "master",
                }
            ],
            "excluded": [],
            "scope": "Screened source snapshot.",
            "restoration": "Inspect source-manifest.json.",
            "qualification": "Unqualified development snapshot.",
            "privacy": "No credential contents intentionally included.",
        }
        self.write_archive()
        self.save_manifest()

    def git(self, *arguments):
        result = subprocess.run(
            ["git", *arguments],
            cwd=self.caller,
            input=b"Checksum regression fixture\n",
            capture_output=True,
            check=True,
            env=dict(
                os.environ,
                GIT_AUTHOR_NAME="Fixture",
                GIT_AUTHOR_EMAIL="fixture@example.invalid",
                GIT_COMMITTER_NAME="Fixture",
                GIT_COMMITTER_EMAIL="fixture@example.invalid",
            ),
        )
        return result.stdout.decode("utf-8")

    def commit(self):
        self.git("add", "--all")
        self.git("commit", "--allow-empty", "-m", "Checksum regression fixture")

    def write_archive(
        self, *, members=None, raw_manifest=None, compression=ZIP_DEFLATED
    ):
        if members is None:
            members = [(self.source_path, self.source_bytes)]
        with ZipFile(self.archive_path, "w", compression=compression) as handle:
            for name, payload in members:
                handle.writestr(name, payload)
            handle.writestr(
                "source-manifest.json",
                json.dumps(self.source_manifest)
                if raw_manifest is None
                else raw_manifest,
            )
        self.refresh_archive_identity()

    def refresh_archive_identity(self):
        payload = self.archive_path.read_bytes()
        blob = hashlib.sha1(
            b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        ).hexdigest()
        self.manifest["archives"][0] = {
            "name": self.archive_path.name,
            "bytes": len(payload),
            "source_files": len(self.source_manifest["files"]),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "git_blob_sha": blob,
            "remote_blob_sha": blob,
            "remote_sha256_verified": True,
            "remote_source_hashes_verified": True,
            "repository_path": self.archive_path.relative_to(self.caller).as_posix(),
        }

    def save_manifest(self):
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=2), encoding="utf-8"
        )
        self.commit()

    def scan(self):
        return self.harness.run_block(
            "secrets", env={"GITHUB_REPOSITORY": "test/fixture"}
        )

    def assert_rejected(self):
        code, outputs, log = self.scan()
        self.assertEqual((code, outputs["status"]), (1, "error"))
        self.assertNotIn("Traceback", log)
        for value in (self.original_head, self.manifest["archives"][0]["sha256"]):
            self.assertNotIn(value, log)

    def test_real_verified_capsule_is_clean_and_all_detectors_remain_active(self):
        baselines = []
        real_run = subprocess.run

        def capture(command, **kwargs):
            result = real_run(command, **kwargs)
            if command[:4] == [os.sys.executable, "-I", "-m", "detect_secrets"]:
                baselines.append(json.loads(Path(kwargs["stdout"].name).read_bytes()))
            return result

        with patch("subprocess.run", side_effect=capture):
            code, outputs, log = self.scan()
        self.assertEqual(
            (code, outputs),
            (0, {"status": "clean", "count": "0", "has_issues": "false"}),
        )
        self.assertEqual(
            baselines[0]["plugins_used"], self.harness.empty["plugins_used"]
        )
        self.assertEqual(
            baselines[0]["filters_used"], self.harness.empty["filters_used"]
        )
        self.assertEqual(len(baselines[0]["plugins_used"]), 27)
        self.assertTrue(baselines[0]["results"])
        self.assertNotIn(self.original_head, log)

    def test_credential_beside_verified_digest_still_fails(self):
        token = (
            "ghp_" + hashlib.sha256(b"offline preservation fixture").hexdigest()[:36]
        )
        self.manifest["privacy"] = token
        self.save_manifest()
        code, outputs, log = self.scan()
        self.assertEqual((code, outputs["status"]), (1, "findings"))
        self.assertGreater(int(outputs["count"]), 0)
        self.assertNotIn(token, log)

    def test_verified_digest_in_an_unverified_field_still_fails(self):
        self.manifest["privacy"] = self.manifest["archives"][0]["sha256"]
        self.save_manifest()
        code, outputs, _ = self.scan()
        self.assertEqual((code, outputs["status"]), (1, "findings"))
        self.assertGreater(int(outputs["count"]), 0)

    def test_credential_hidden_in_checksum_field_is_not_accepted(self):
        for key in ("sha256", "git_blob_sha", "remote_blob_sha"):
            with self.subTest(field=key):
                original = self.manifest["archives"][0][key]
                self.manifest["archives"][0][key] = hashlib.sha256(
                    ("unrelated hexadecimal credential " + key).encode()
                ).hexdigest()
                if key != "sha256":
                    self.manifest["archives"][0][key] = self.manifest["archives"][0][
                        key
                    ][:40]
                self.save_manifest()
                self.assert_rejected()
                self.manifest["archives"][0][key] = original

    def test_wrong_archive_or_source_byte_identity_is_rejected(self):
        self.archive_path.write_bytes(self.archive_path.read_bytes() + b"tampering")
        self.commit()
        self.assert_rejected()
        self.source_manifest["files"][0]["sha256"] = hashlib.sha256(
            b"forged"
        ).hexdigest()
        self.write_archive()
        self.save_manifest()
        self.assert_rejected()

    def test_bad_repository_path_or_unknown_schema_is_rejected(self):
        archive = self.manifest["archives"][0]
        archive["repository_path"] = "../outside.zip"
        self.save_manifest()
        self.assert_rejected()
        archive["repository_path"] = self.archive_path.relative_to(
            self.caller
        ).as_posix()
        self.manifest["unknown_schema_field"] = "unsupported"
        self.save_manifest()
        self.assert_rejected()

    def test_unknown_source_schema_is_rejected(self):
        self.source_manifest["files"][0]["unknown_schema_field"] = "unsupported"
        self.write_archive()
        self.save_manifest()
        self.assert_rejected()

    def test_unsafe_zip_paths_and_entry_sets_are_rejected(self):
        for path in (
            "../outside.py",
            "/absolute.py",
            "worktrees\\source.py",
            "a/./b.py",
            ".",
        ):
            with self.subTest(path=path):
                self.source_manifest["files"][0]["archive_path"] = path
                self.write_archive(members=[(path, self.source_bytes)])
                self.save_manifest()
                self.assert_rejected()
        self.source_manifest["files"][0]["archive_path"] = self.source_path
        self.write_archive(
            members=[(self.source_path, self.source_bytes), ("extra.py", b"extra")]
        )
        self.save_manifest()
        self.assert_rejected()

    def test_corrupt_crc_is_rejected_even_with_matching_archive_hashes(self):
        self.write_archive(compression=ZIP_STORED)
        with ZipFile(self.archive_path) as handle:
            entry = handle.getinfo(self.source_path)
            offset = (
                entry.header_offset
                + 30
                + len(entry.filename.encode())
                + len(entry.extra)
            )
        payload = bytearray(self.archive_path.read_bytes())
        payload[offset] ^= 1
        self.archive_path.write_bytes(payload)
        self.refresh_archive_identity()
        self.save_manifest()
        self.assert_rejected()

    def test_zip_symlink_is_rejected(self):
        entry = ZipInfo(self.source_path)
        entry.create_system = 3
        entry.external_attr = 0o120777 << 16
        self.write_archive(members=[(entry, self.source_bytes)])
        self.save_manifest()
        self.assert_rejected()

    @unittest.skipIf(
        os.name == "nt", "Native symlink fixture is exercised by Ubuntu CI"
    )
    def test_filesystem_symlink_is_rejected(self):
        outside = self.harness.runner / "archive.zip"
        self.archive_path.rename(outside)
        self.archive_path.symlink_to(outside)
        self.commit()
        self.assert_rejected()

    def test_unavailable_or_unrelated_git_commit_is_rejected(self):
        self.manifest["source_checkouts"][0]["head"] = hashlib.sha256(
            b"unavailable Git object"
        ).hexdigest()[:40]
        self.save_manifest()
        self.assert_rejected()
        self.manifest["source_checkouts"][0]["head"] = self.git(
            "commit-tree", "HEAD^{tree}"
        ).strip()
        self.git(
            "replace", self.manifest["source_checkouts"][0]["head"], self.original_head
        )
        self.save_manifest()
        self.assert_rejected()

    def test_malformed_or_ambiguous_manifest_is_rejected(self):
        original = self.manifest_path.read_text()
        for raw in (
            "{" + original,
            original.replace('"excluded": []', '"excluded": [], "excluded": []'),
            original.replace('"excluded": []', '"excluded": [NaN]'),
        ):
            with self.subTest(case=raw[:1]):
                self.manifest_path.write_text(raw)
                self.commit()
                self.assert_rejected()

    def test_malformed_source_manifest_is_rejected(self):
        self.write_archive(raw_manifest=b"{invalid JSON")
        self.save_manifest()
        self.assert_rejected()

    def test_source_metadata_cannot_escape_its_verified_checkout(self):
        source = self.source_manifest["files"][0]
        for key, value in (
            ("source", r"C:\fixture\repo\..\outside.py"),
            ("original_branch", "unrelated"),
            (
                "original_head",
                hashlib.sha256(b"unrelated source head").hexdigest()[:40],
            ),
            ("bytes", len(self.source_bytes) + 1),
        ):
            with self.subTest(field=key):
                original = source[key]
                source[key] = value
                self.write_archive()
                self.save_manifest()
                self.assert_rejected()
                source[key] = original

    def test_uncommitted_capsule_or_wrong_repository_is_rejected(self):
        self.manifest["scope"] = "Uncommitted capsule metadata."
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2))
        self.assert_rejected()
        self.save_manifest()
        code, outputs, _ = self.harness.run_block(
            "secrets", env={"GITHUB_REPOSITORY": "unrelated/repository"}
        )
        self.assertEqual((code, outputs["status"]), (1, "error"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
