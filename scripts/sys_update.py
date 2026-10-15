#!/usr/bin/env python3
"""Minimal manifest-only updater for ArtCraft releases.

This script reads versions.json, queries the public GitHub releases API for each
ArtCraft app, adds any missing versions that have a published sha256 AppImage,
and writes the manifest back in sorted order.

It intentionally avoids the full repo update workflow, mirror upload logic, and
GitHub CLI requirements.
"""

import base64
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "versions.json"

ASSET = re.compile(r"^(?P<bin>[a-z0-9]+)-(?P<version>\d+\.\d+\.\d+)-linux-x86_64\.AppImage$")


def vkey(version):
    return tuple(int(part) for part in version.split("."))


def fetch_releases(repo):
    url = f"https://api.github.com/repos/{repo}/releases"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def discover(repo):
    found = {}
    releases = fetch_releases(repo)
    for rel in releases:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        for asset in rel.get("assets", []):
            name = asset.get("name")
            match = ASSET.match(name or "")
            if not match:
                continue
            digest = asset.get("digest") or ""
            if not digest.startswith("sha256:"):
                continue
            version = match.group("version")
            found[version] = {
                "tag": rel.get("tag_name"),
                "file": name,
                "bin": match.group("bin"),
                "hash": "sha256-" + base64.b64encode(bytes.fromhex(digest.removeprefix("sha256:"))).decode(),
            }
    return found


def main():
    with MANIFEST.open() as f:
        data = json.load(f)

    changed = []
    for app, meta in data["apps"].items():
        repo = meta["repo"]
        try:
            upstream = discover(repo)
        except Exception as exc:
            print(f"{app}: failed to fetch {repo}: {exc}")
            continue

        missing = sorted(set(upstream) - set(meta["versions"]), key=vkey)
        for version in missing:
            meta["versions"][version] = upstream[version]
            changed.append(f"{app} {version}")

    if not changed:
        print("No new versions found.")
        return 0

    for info in data["apps"].values():
        info["versions"] = dict(sorted(info["versions"].items(), key=lambda kv: vkey(kv[0])))

    with MANIFEST.open("w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print("Updated versions.json:")
    for item in changed:
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
