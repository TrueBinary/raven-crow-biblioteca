"""Approved Raven Crow Instagram media -> private GitHub -> public Render DNS.

No Buffer mutations, no image rendering, no n8n or CorteFlow daemon changes.
Require an approved, SHA256-locked manifest. Public delivery must validate
before a caller is allowed to schedule or edit a Buffer post.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


DOMAIN = "ravencrow.cloud"
PUBLIC_BASE = f"https://{DOMAIN}/instagram-media"
DEFAULT_REPO = Path(r"D:\CorteFlow\work\raven-crow-biblioteca")
MAGIC = {"image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff"}
MAX_BYTES = 12 * 1024 * 1024


class TransportError(RuntimeError):
    pass


@dataclass(frozen=True)
class Media:
    source: Path
    sha256: str
    size: int
    mime: str
    extension: str

    @property
    def relative_path(self) -> str:
        return f"public/instagram-media/{self.sha256}{self.extension}"

    @property
    def url(self) -> str:
        return f"{PUBLIC_BASE}/{self.sha256}{self.extension}"


def validate_manifest(m: dict) -> Media:
    if m.get("editorial_status") != "approved":
        raise TransportError("editorial approval required")
    if m.get("qa_approved") is not True or m.get("rights_verified") is not True:
        raise TransportError("visual QA and usage rights must be verified")
    raw_path = m.get("media_path")
    if not isinstance(raw_path, str) or not raw_path:
        raise TransportError("missing media_path")
    source = Path(raw_path)
    if not source.is_absolute() or not source.is_file():
        raise TransportError("absolute local media path required")
    suffix = source.suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg"):
        raise TransportError("only PNG and JPEG files supported")
    size = source.stat().st_size
    if not 16 <= size <= MAX_BYTES:
        raise TransportError("image file size out of bounds")
    with source.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    expected = m.get("sha256", "")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected) or expected != digest:
        raise TransportError("sha256 mismatch")
    try:
        with Image.open(source) as im:
            fmt, dims = im.format, im.size
            im.verify()
    except Exception as e:
        raise TransportError("invalid image data") from e
    if dims != (1080, 1350):
        raise TransportError("Instagram photo must be exactly 1080x1350")
    if fmt == "PNG" and suffix == ".png":
        mime, ext = "image/png", ".png"
    elif fmt == "JPEG" and suffix in (".jpg", ".jpeg"):
        mime, ext = "image/jpeg", ".jpg"
    else:
        raise TransportError("file extension does not match image format")
    return Media(source=source, sha256=digest, size=size, mime=mime, extension=ext)


def probe_public(asset: Media, opener=urllib.request.urlopen) -> bool:
    """No off-domain redirect, and both HEAD metadata and GET magic validated."""
    for method in ("HEAD", "GET"):
        headers = {"User-Agent": "RavenCrow-MediaGate/1.0"}
        if method == "GET":
            headers["Range"] = "bytes=0-7"
        req = urllib.request.Request(asset.url, method=method, headers=headers)
        with opener(req, timeout=8) as resp:
            if resp.geturl() != asset.url:
                raise TransportError("public media redirected or URL changed from canonical HTTPS asset")
            status = getattr(resp, "status", None)
            if status is None:
                status = resp.getcode()
            if (method == "HEAD" and status != 200) or (method == "GET" and status not in (200, 206)):
                raise TransportError(f"invalid {method} HTTP status {status}")
            ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
            if ctype != asset.mime:
                raise TransportError(f"invalid {method} media type {ctype}")
            if method == "HEAD":
                length = resp.headers.get("content-length")
                if length is None or int(length) != asset.size:
                    raise TransportError("public Content-Length does not match media file")
            else:
                signature = resp.read(8)
                if not signature.startswith(MAGIC[asset.mime]):
                    raise TransportError("public GET image signature invalid")
    return True


def wait_for_public(asset: Media, attempts: int = 20, delay_s: int = 10) -> bool:
    last = "no public response"
    for attempt in range(attempts):
        try:
            return probe_public(asset)
        except (TransportError, OSError, urllib.error.URLError, ValueError) as e:
            last = str(e)
        if attempt < attempts - 1:
            time.sleep(delay_s)
    raise TransportError("public Render/DNS URL not verified; do not schedule: " + last)


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=150
    )
    return result.stdout.strip()


def publish(asset: Media, repo_root: Path = DEFAULT_REPO, probe=wait_for_public,
            expected_origin: str = "https://github.com/TrueBinary/raven-crow-biblioteca.git") -> dict:
    """Fast-forward media-only push in an isolated sparse worktree. Fail closed."""
    repo_root = Path(repo_root).resolve()
    if not (repo_root / ".git").exists():
        raise TransportError("authorized local Git checkout not found")
    try:
        actual_origin = git(repo_root, "remote", "get-url", "origin")
    except (subprocess.CalledProcessError, OSError) as e:
        raise TransportError("cannot verify Git remote origin") from e
    if actual_origin.replace("\\", "/").rstrip("/") != expected_origin.replace("\\", "/").rstrip("/"):
        raise TransportError("Git remote origin is not the approved Raven Crow repository")
    try:
        git(repo_root, "fetch", "origin", "main")
    except (subprocess.CalledProcessError, OSError) as e:
        raise TransportError("cannot fetch private GitHub: no Buffer post") from e
    scratch = Path(tempfile.mkdtemp(prefix="raven-ig-media-"))
    worktree = scratch / "site"
    worktree_created = False
    succeeded = False
    try:
        git(repo_root, "worktree", "add", "--detach", "--no-checkout",
            str(worktree), "origin/main")
        worktree_created = True
        git(worktree, "sparse-checkout", "init", "--cone")
        git(worktree, "sparse-checkout", "set", "public/instagram-media")
        git(worktree, "checkout", "HEAD")

        dest = worktree / Path(asset.relative_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            with dest.open("rb") as f:
                old_digest = hashlib.file_digest(f, "sha256").hexdigest()
            if old_digest != asset.sha256:
                raise TransportError("existing immutable media hash differs")
        else:
            shutil.copy2(asset.source, dest)
        with dest.open("rb") as copied:
            copied_digest = hashlib.file_digest(copied, "sha256").hexdigest()
        if copied_digest != asset.sha256 or dest.stat().st_size != asset.size:
            raise TransportError("media modified since approval; refuse commit")
        git(worktree, "add", "--", asset.relative_path)
        staged = git(worktree, "diff", "--cached", "--name-only")
        if staged and staged.splitlines() != [asset.relative_path]:
            raise TransportError("unexpected staged files: refuse publishing")
        if staged:
            git(worktree, "diff", "--cached", "--check")
            git(worktree, "commit", "-m", f"media: approved Instagram asset {asset.sha256[:12]}")
            # Plain push: if another agent moved main, STOP; never force or rebase.
            git(worktree, "push", "origin", "HEAD:main")
        if probe(asset) is not True:
            raise TransportError("public media probe did not approve")
        succeeded = True
        return {"status": "ready", "url": asset.url, "sha256": asset.sha256, "bytes": asset.size}
    except (subprocess.CalledProcessError, OSError, ValueError) as e:
        raise TransportError(
            "media not ready; preserve manifest and do not schedule. "
            f"Isolated worktree: {worktree}"
        ) from e
    finally:
        if succeeded and worktree_created:
            try:
                git(repo_root, "worktree", "remove", str(worktree))
                scratch.rmdir()
            except (subprocess.CalledProcessError, OSError):
                pass  # Safe abandoned scratch; published URL remains valid.


def main() -> int:
    parser = argparse.ArgumentParser(description="Approved Raven Crow IG media -> public site")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO))
    opts = parser.parse_args()
    try:
        with Path(opts.manifest).open(encoding="utf8") as f:
            asset = validate_manifest(json.load(f))
        print(json.dumps(publish(asset, Path(opts.repo_root)), ensure_ascii=False))
        return 0
    except (TransportError, OSError, ValueError, json.JSONDecodeError) as e:
        print(json.dumps({"status": "blocked", "reason": str(e)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
