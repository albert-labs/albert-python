#!/usr/bin/env bash
set -euo pipefail

# Resolve the SDK runtime dependencies (no dev extras) and fail if pip-audit
# reports any vulnerability. This matches what the Lambda layer installs.
# AUDIT_PYTHON overrides marker evaluation (for example "3.14"); otherwise
# .python-version is used. The published layer matrix is Python 3.11–3.14.
# Python 3.10 still resolves dnspython 2.8.0 because 2.9.2 requires 3.11+.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed. Install from https://docs.astral.sh/uv/" >&2
    exit 2
fi

if [[ -n "${AUDIT_PYTHON:-}" ]]; then
    PYTHON="$AUDIT_PYTHON"
else
    PYTHON="$(tr -d '[:space:]' < .python-version)"
fi

EXPORT="$(mktemp)"
PINS="$(mktemp)"
cleanup() { rm -f "$EXPORT" "$PINS"; }
trap cleanup EXIT

echo "==> Resolving dependencies for ${PYTHON}..."
# uv.lock is gitignored, so CI resolves from pyproject.toml on each run.
uv export --python "$PYTHON" --no-dev --no-hashes --no-emit-project -o "$EXPORT" >/dev/null

# Marker selection follows AUDIT_PYTHON. pip-audit itself runs on CPython 3.13
# because some uv-managed interpreters cannot create the temporary env it uses.
uvx --python 3.13 --with packaging python - "$EXPORT" "$PINS" "$PYTHON" <<'PY'
import sys
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement

src, dst, requested = sys.argv[1], sys.argv[2], sys.argv[3]
env = default_environment()
version = requested
if version.count(".") == 1:
    version = f"{version}.99"
env["python_version"] = ".".join(version.split(".")[:2])
env["python_full_version"] = version
pins = []
for line in Path(src).read_text().splitlines():
    if not line.strip() or line.lstrip().startswith("#") or line[:1].isspace():
        continue
    req = Requirement(line.strip())
    if req.marker is not None and not req.marker.evaluate(env):
        continue
    pins.append(line.split(";", 1)[0].strip())
Path(dst).write_text("\n".join(sorted(set(pins))) + "\n")
print(f"==> Auditing {len(set(pins))} pinned packages for Python {env['python_full_version']}")
PY

echo "==> Running pip-audit 2.10.1..."
uvx --python 3.13 pip-audit==2.10.1 -r "$PINS" --no-deps --aliases
