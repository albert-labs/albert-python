import argparse
import re
import sys
from pathlib import Path


def extract_version(file_content: str) -> str:
    match = re.search(r'__version__\s*=\s*[\'"]([^\'"]+)[\'"]', file_content)
    if match:
        return match.group(1)
    else:
        raise ValueError(f"Version string not found in file\n{file_content}")


def main(release_tag: str) -> None:
    version_file = "src/albert/__init__.py"
    version_path = Path(__file__).parents[1] / version_file

    package_version = extract_version(version_path.read_text())
    release_version = release_tag.lstrip("v")

    if package_version == release_version:
        print(f"Release version '{release_version}' matches package '{package_version}'")
    else:
        print(f"Release version '{release_version}' does not match package '{package_version}'")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--tag", required=True)
    args = parser.parse_args()

    main(args.tag)
