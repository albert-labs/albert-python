import argparse
import sys
from os import popen
from pathlib import Path

from packaging import version
from validate_release_tag import extract_version


def is_version_bump(new_version: str, old_version: str) -> bool:
    new_version_parsed = version.parse(new_version)
    old_version_parsed = version.parse(old_version)
    return new_version_parsed > old_version_parsed


def main(base_branch: str):
    version_file = "src/albert/__init__.py"

    local_path = Path(__file__).parents[1] / version_file
    local_version = extract_version(local_path.read_text())

    with popen(f"git fetch origin && git show {base_branch}:{version_file}") as fh:
        base_version = extract_version(fh.read())

    if is_version_bump(local_version, base_version):
        print(f"Version bump detected: {base_version} -> {local_version}")
        sys.exit(0)
    else:
        print(f"No version bump detected: {local_version} <= {base_version}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--base", default="origin/main")
    args = parser.parse_args()

    main(args.base)
