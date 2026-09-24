#!/usr/bin/env python3
"""Writes a JSON catalog of every public albert-python Lambda layer version.

AWS gives other accounts no way to list our layers, so this catalog is how users
discover them. It is published at a stable, unversioned URL on the docs site and
rendered as a table on the AWS Lambda layer docs page.

Only layers named ``albert-python-py<runtime>-<x86_64|arm64>`` are considered, and
only versions whose description was written by ``publish-lambda-layer.sh``
(``albert-python <sdk version> | ...``). A version is included only when its
resource policy lets any account call ``lambda:GetLayerVersion``, so versions
restricted to one account never appear.

Requires boto3 and AWS credentials for the account that owns the layers.
"""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

DESCRIPTION_RE = re.compile(r"^albert-python (?P<sdk_version>\S+) \|")
LAYER_NAME_RE = re.compile(r"^albert-python-py(?P<major>\d)(?P<minor>\d+)-(?P<arch>x86_64|arm64)$")


def is_public(policy: dict) -> bool:
    for statement in policy.get("Statement", []):
        actions = statement.get("Action")
        actions = [actions] if isinstance(actions, str) else actions or []
        if (
            statement.get("Effect") == "Allow"
            and statement.get("Principal") in ("*", {"AWS": "*"})
            and "lambda:GetLayerVersion" in actions
            and not statement.get("Condition")
        ):
            return True
    return False


def version_is_public(client, layer_name: str, version: int) -> bool:
    try:
        response = client.get_layer_version_policy(LayerName=layer_name, VersionNumber=version)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise
    return is_public(json.loads(response["Policy"]))


def list_region(region: str) -> list[dict]:
    client = boto3.client("lambda", region_name=region)
    candidates: list[dict] = []
    # boto3 paginators follow NextMarker until the last page.
    for page in client.get_paginator("list_layers").paginate():
        for layer in page["Layers"]:
            name = layer["LayerName"]
            named = LAYER_NAME_RE.match(name)
            if not named:
                continue
            for versions_page in client.get_paginator("list_layer_versions").paginate(
                LayerName=name
            ):
                for version in versions_page["LayerVersions"]:
                    description = version.get("Description", "")
                    described = DESCRIPTION_RE.match(description)
                    if not described:
                        continue
                    candidates.append(
                        {
                            "sdk_version": described["sdk_version"],
                            "python": f"{named['major']}.{named['minor']}",
                            "architecture": named["arch"],
                            "region": region,
                            "layer_name": name,
                            "layer_version": version["Version"],
                            "arn": version["LayerVersionArn"],
                            "created": version["CreatedDate"],
                            "description": description,
                        }
                    )

    with ThreadPoolExecutor(max_workers=8) as pool:
        public = list(
            pool.map(
                lambda e: version_is_public(client, e["layer_name"], e["layer_version"]),
                candidates,
            )
        )
    return [entry for entry, is_pub in zip(candidates, public, strict=True) if is_pub]


def python_sort_key(python: str) -> tuple[int, ...]:
    return tuple(int(part) for part in python.split("."))


def sdk_version_sort_key(version: str) -> tuple:
    """Orders releases above their pre-releases (1.2.0 > 1.2.0rc1); unparsable versions last."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", version)
    if not match:
        return (0,)
    major, minor, patch, suffix = match.groups()
    return (1, int(major), int(minor), int(patch), suffix == "", suffix)


def build_catalog(regions: list[str]) -> dict:
    layers = [entry for region in regions for entry in list_region(region)]
    layers.sort(key=lambda e: (e["region"], e["architecture"]))
    layers.sort(key=lambda e: python_sort_key(e["python"]), reverse=True)
    layers.sort(key=lambda e: sdk_version_sort_key(e["sdk_version"]), reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "layers": layers,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--regions", required=True, help="Comma-separated AWS regions")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    if not regions:
        raise SystemExit("--regions must not be empty.")

    catalog = build_catalog(regions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"Wrote {len(catalog['layers'])} public layer version(s) to {args.output}")


if __name__ == "__main__":
    main()
