"""Safe Instagram media transport: tests never touch production Git, Buffer or DNS."""
import hashlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from ops import instagram_media_transport as media


class TransportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pic = self.root / "approved.png"
        Image.new("RGB", (1080, 1350), "red").save(self.pic, format="PNG")
        self.digest = hashlib.sha256(self.pic.read_bytes()).hexdigest()
        self.manifest = dict(
            editorial_status="approved", qa_approved=True, rights_verified=True,
            media_path=str(self.pic), sha256=self.digest
        )

    def test_requires_explicit_approval(self):
        for key, value in (("editorial_status", "draft"), ("qa_approved", False),
                           ("rights_verified", False), ("sha256", "0"*64)):
            with self.subTest(key=key):
                bad = dict(self.manifest, **{key: value})
                with self.assertRaises(media.TransportError):
                    media.validate_manifest(bad)

    def test_requires_portrait_real_image(self):
        bad = self.root / "wrong.png"
        Image.new("RGB", (100, 100), "red").save(bad, format="PNG")
        data = dict(self.manifest, media_path=str(bad),
                    sha256=hashlib.sha256(bad.read_bytes()).hexdigest())
        with self.assertRaises(media.TransportError):
            media.validate_manifest(data)

    def test_content_addressed_url(self):
        m = media.validate_manifest(self.manifest)
        self.assertEqual(m.url, "https://ravencrow.cloud/instagram-media/" + self.digest + ".png")
        self.assertEqual(m.relative_path, "public/instagram-media/" + self.digest + ".png")
        self.assertEqual(m.mime, "image/png")

    def test_missing_file_and_bad_extension_rejected(self):
        with self.assertRaises(media.TransportError):
            media.validate_manifest(dict(self.manifest, media_path=str(self.root / "no.png")))
        bad = self.root / "image.txt"
        bad.write_bytes(self.pic.read_bytes())
        with self.assertRaises(media.TransportError):
            media.validate_manifest(dict(self.manifest, media_path=str(bad)))

    def test_probe_rejects_untrusted_redirect_or_mismatch(self):
        m = media.validate_manifest(self.manifest)
        class FakeResp:
            status = 200
            def __init__(self, url, mime, n):
                self.url = url
                self.headers = {"content-type": mime, "content-length": str(n)}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def geturl(self): return self.url
            def read(self, n=-1): return b"\x89PNG\r\n\x1a\n"[:n]
        def bad_redirect(request, timeout=8):
            return FakeResp("https://raw.githubusercontent.com/file", m.mime, m.size)
        with self.assertRaises(media.TransportError):
            media.probe_public(m, opener=bad_redirect)
        def bad_size(request, timeout=8):
            return FakeResp(m.url, m.mime, m.size + 4)
        with self.assertRaises(media.TransportError):
            media.probe_public(m, opener=bad_size)

    def test_probe_rejects_same_domain_redirect_to_other_path(self):
        m = media.validate_manifest(self.manifest)
        class FakeResp:
            status = 200
            headers = {"content-type": "image/png"}
            def __init__(self):
                self.headers = dict(self.headers, **{"content-length": str(m.size)})
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def geturl(self): return "https://ravencrow.cloud/other-image.png"
            def read(self, n=-1): return b"\x89PNG\r\n\x1a\n"[:n]
        with self.assertRaises(media.TransportError):
            media.probe_public(m, opener=lambda req, timeout=8: FakeResp())

    def test_probe_success_with_png_magic(self):
        m = media.validate_manifest(self.manifest)
        class FakeResp:
            status = 200
            headers = {"content-type": "image/png"}
            def __init__(self, url, n): self.url = url; self.headers = dict(self.headers, **{"content-length": str(n)})
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def geturl(self): return self.url
            def read(self, n=-1): return b"\x89PNG\r\n\x1a\n"[:n]
        self.assertTrue(media.probe_public(m, opener=lambda req, timeout=8: FakeResp(m.url, m.size)))

    def test_publishes_only_asset_to_private_git_origin(self):
        origin = self.root / "origin.git"
        site = self.root / "site"
        self.git(self.root, "init", "--bare", "--initial-branch=main", str(origin))
        self.git(self.root, "clone", str(origin), str(site))
        self.git(site, "config", "user.name", "Raven Test")
        self.git(site, "config", "user.email", "raven-test@example.invalid")
        (site / "public").mkdir()
        (site / "public" / "index.html").write_text("portal", encoding="utf8")
        self.git(site, "add", "--", "public/index.html")
        self.git(site, "commit", "-m", "seed")
        self.git(site, "push", "origin", "HEAD:main")
        # The real CorteFlow checkout may be dirty; worktree publication must not edit it.
        (site / "public" / "index.html").write_text("unpublished local edits", encoding="utf8")
        (site / "local-untracked.txt").write_text("keep", encoding="utf8")
        m = media.validate_manifest(self.manifest)
        report = media.publish(m, repo_root=site, probe=lambda asset: True, expected_origin=str(origin))
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["url"], m.url)
        self.assertEqual((site / "public" / "index.html").read_text(), "unpublished local edits")
        self.assertEqual((site / "local-untracked.txt").read_text(), "keep")
        tree = self.git(site, "ls-tree", "-r", "--name-only", "origin/main")
        self.assertIn(m.relative_path, tree)
        self.assertIn("public/index.html", tree)
        again = media.publish(m, repo_root=site, probe=lambda asset: True, expected_origin=str(origin))
        self.assertEqual(again["status"], "ready")
        self.assertEqual(self.git(site, "rev-list", "--count", "origin/main"), "2")

    def test_wrong_origin_rejected_before_any_push(self):
        origin = self.root / "other.git"
        site = self.root / "site"
        self.git(self.root, "init", "--bare", "--initial-branch=main", str(origin))
        self.git(self.root, "clone", str(origin), str(site))
        self.git(site, "config", "user.name", "Raven Test")
        self.git(site, "config", "user.email", "raven-test@example.invalid")
        (site / "public").mkdir()
        (site / "public" / "index.html").write_text("portal")
        self.git(site, "add", "--", "public/index.html")
        self.git(site, "commit", "-m", "seed")
        self.git(site, "push", "origin", "HEAD:main")
        with self.assertRaises(media.TransportError):
            media.publish(media.validate_manifest(self.manifest), repo_root=site,
                          probe=lambda asset: True)
        self.assertEqual(self.git(site, "rev-list", "--count", "origin/main"), "1")

    def test_tamper_after_validation_blocks_upload(self):
        origin = self.root / "origin.git"
        site = self.root / "site"
        self.git(self.root, "init", "--bare", "--initial-branch=main", str(origin))
        self.git(self.root, "clone", str(origin), str(site))
        self.git(site, "config", "user.name", "Raven Test")
        self.git(site, "config", "user.email", "raven-test@example.invalid")
        (site / "public").mkdir()
        (site / "public" / "index.html").write_text("portal")
        self.git(site, "add", "--", "public/index.html")
        self.git(site, "commit", "-m", "seed")
        self.git(site, "push", "origin", "HEAD:main")
        approved = media.validate_manifest(self.manifest)
        Image.new("RGB", (1080, 1350), "blue").save(self.pic, format="PNG")
        with self.assertRaises(media.TransportError):
            media.publish(approved, repo_root=site,
                          probe=lambda asset: True, expected_origin=str(origin))
        self.assertEqual(self.git(site, "rev-list", "--count", "origin/main"), "1")

    @staticmethod
    def git(path, *args):
        return subprocess.run(["git", "-C", str(path), *args], check=True,
                              capture_output=True, text=True).stdout.strip()


if __name__ == "__main__":
    unittest.main()
