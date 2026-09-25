#!/usr/bin/env python3
"""Collects published Lambda layer ARNs and records them in the GitHub release.

Each matrix job appends tab-separated lines to a manifest file
(``<region> <runtime> <arch> <layer_arn> <published|reused>``, written by
``publish-lambda-layer.sh --manifest``) and persists it to the workspace. This
script runs once after every matrix job has finished: it merges the manifests
into a Markdown table, writes that table to ``--output`` (stored as a CircleCI
artifact), and, when the pipeline runs on a release tag, upserts the table into
the GitHub release body between marker comments so re-runs replace rather than
duplicate it.

Only the standard library is used so the script runs on a plain cimg/python image.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

START_MARKER = "<!-- lambda-layers:start -->"
END_MARKER = "<!-- lambda-layers:end -->"
# GITHUB_API_URL follows the GitHub Actions convention and lets tests point at a mock server.
GITHUB_API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")


def read_manifests(manifest_dir: Path) -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []
    for path in sorted(manifest_dir.glob("*.tsv")):
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 5:
                raise SystemExit(
                    f"{path}: expected 5 tab-separated fields, got {len(parts)}: {line!r}"
                )
            rows.append(tuple(parts))  # type: ignore[arg-type]
    return rows


def runtime_sort_key(runtime: str) -> tuple[int, ...]:
    return tuple(int(part) for part in runtime.split("."))


def render_table(rows: list[tuple[str, str, str, str, str]], sdk_version: str) -> str:
    ordered = sorted(rows, key=lambda r: (runtime_sort_key(r[1]), r[2], r[0]))
    lines = [
        f"## Lambda layers ({sdk_version})",
        "",
        "Layer versions containing this release. Pin your function to one of these ARNs. "
        "See the [AWS Lambda layer docs](https://docs.developer.albertinvent.com/albert-python/latest/lambda/) "
        "for how to attach a layer.",
        "",
        "| Runtime | Architecture | Region | Layer ARN |",
        "|---|---|---|---|",
    ]
    for region, runtime, arch, arn, _status in ordered:
        lines.append(f"| python{runtime} | {arch} | {region} | `{arn}` |")
    return "\n".join(lines) + "\n"


def upsert_section(body: str, section: str) -> str:
    block = f"{START_MARKER}\n{section}{END_MARKER}"
    if START_MARKER in body and END_MARKER in body:
        head, rest = body.split(START_MARKER, 1)
        _old, tail = rest.split(END_MARKER, 1)
        return f"{head}{block}{tail}"
    body = body.rstrip("\n")
    return f"{body}\n\n{block}\n" if body else f"{block}\n"


def github_request(method: str, url: str, token: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_release(
    repo: str, tag: str, token: str, attempts: int = 6, delay_s: float = 10.0
) -> dict:
    """Fetches the release for ``tag``, retrying while GitHub finishes creating it."""
    url = f"{GITHUB_API}/repos/{repo}/releases/tags/{tag}"
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return github_request("GET", url, token)
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            last_error = exc
            print(
                f"Release for {tag} not found yet (attempt {attempt}/{attempts}); retrying in {delay_s:.0f}s"
            )
            time.sleep(delay_s)
    raise SystemExit(f"No GitHub release found for tag {tag}: {last_error}")


def update_release_notes(repo: str, tag: str, token: str, section: str) -> None:
    release = fetch_release(repo, tag, token)
    new_body = upsert_section(release.get("body") or "", section)
    if new_body == release.get("body"):
        print(f"Release notes for {tag} already contain this table; nothing to do.")
        return
    github_request(
        "PATCH", f"{GITHUB_API}/repos/{repo}/releases/{release['id']}", token, {"body": new_body}
    )
    print(f"Updated release notes for {tag}: {release.get('html_url', '')}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--manifest-dir", required=True, type=Path, help="Directory of *.tsv manifests"
    )
    parser.add_argument("--sdk-version", required=True)
    parser.add_argument(
        "--output", required=True, type=Path, help="Where to write the Markdown table"
    )
    parser.add_argument(
        "--tag", default="", help="Release tag; when empty the GitHub release is not touched"
    )
    parser.add_argument(
        "--repo",
        default="",
        help="owner/name of the GitHub repository (defaults to CIRCLE_PROJECT_USERNAME/CIRCLE_PROJECT_REPONAME)",
    )
    args = parser.parse_args()

    rows = read_manifests(args.manifest_dir)
    if not rows:
        raise SystemExit(f"No layer manifests found in {args.manifest_dir}")

    section = render_table(rows, args.sdk_version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(section)
    print(section)

    if not args.tag:
        print("Not a release tag pipeline; leaving GitHub release notes untouched.")
        return

    # GITHUB_TOKEN_ALBERT_LABS is the repo token in the CircleCI "dev" context.
    token = os.environ.get("GITHUB_TOKEN_ALBERT_LABS") or os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit(
            "GITHUB_TOKEN_ALBERT_LABS is not set. The layers above were published, but their "
            "ARNs could not be written to the GitHub release. Check the CircleCI dev context."
        )

    repo = args.repo or "/".join(
        filter(
            None,
            (
                os.environ.get("CIRCLE_PROJECT_USERNAME", ""),
                os.environ.get("CIRCLE_PROJECT_REPONAME", ""),
            ),
        )
    )
    if repo.count("/") != 1:
        raise SystemExit("Could not determine the GitHub repository; pass --repo owner/name.")

    update_release_notes(repo, args.tag, token, section)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(
            f"GitHub API error {exc.code} for {exc.url}: {exc.read().decode(errors='replace')}",
            file=sys.stderr,
        )
        sys.exit(1)
