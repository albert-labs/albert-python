#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: .circleci/scripts/build-lambda-layer.sh --version <sdk_version> --runtime <3.12> --arch <x86_64|arm64>

Builds an AWS Lambda layer zip for the Albert SDK using a Lambda base image.
Outputs the zip path on success.
EOF
}

SDK_VERSION=""
RUNTIME=""
ARCH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      SDK_VERSION="$2"
      shift 2
      ;;
    --runtime)
      RUNTIME="$2"
      shift 2
      ;;
    --arch)
      ARCH="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$SDK_VERSION" || -z "$RUNTIME" || -z "$ARCH" ]]; then
  echo "Missing required arguments." >&2
  usage
  exit 1
fi

if [[ ! "$SDK_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(\.?(a|b|rc|dev)[0-9]+)?$ ]]; then
  echo "Invalid --version. Expected semver (e.g. 1.2.3)." >&2
  exit 1
fi

if [[ ! "$RUNTIME" =~ ^[0-9]+\.[0-9]+$ ]]; then
  echo "Invalid --runtime. Expected format: 3.12" >&2
  exit 1
fi

if [[ "$ARCH" != "x86_64" && "$ARCH" != "arm64" ]]; then
  echo "Invalid --arch. Expected x86_64 or arm64." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required but not installed." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="${ROOT_DIR}/dist/lambda"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR" 2>/dev/null || true
  if command -v sudo >/dev/null 2>&1; then
    sudo -n rm -rf "$TMP_DIR" 2>/dev/null || true
  fi
}
trap cleanup EXIT

mkdir -p "$OUT_DIR"

IMAGE="public.ecr.aws/lambda/python:${RUNTIME}"
PLATFORM="linux/amd64"
ARCH_SUFFIX="x86_64"
if [[ "$ARCH" == "arm64" ]]; then
  PLATFORM="linux/arm64"
  ARCH_SUFFIX="arm64"
fi

ZIP_NAME="albert-layer-${SDK_VERSION}-py${RUNTIME}-${ARCH_SUFFIX}.zip"
ZIP_PATH="${OUT_DIR}/${ZIP_NAME}"

# Install packages inside the Lambda image (only step that needs Docker)
docker run \
  --rm \
  --platform "${PLATFORM}" \
  --entrypoint /bin/bash \
  --user "$(id -u):$(id -g)" \
  --network host \
  -v "${TMP_DIR}:/work" \
  "${IMAGE}" \
  -c "
    set -euo pipefail
    python -m pip install --no-cache-dir --only-binary numpy,pandas albert==${SDK_VERSION} -t /work/python 1>&2
    PYTHONPATH=/work/python python -c 'import albert' 1>&2
  " 1>&2

# Cleanup and zip on the host — no dependency on tools inside the Lambda image
python3 - "${TMP_DIR}/python" "${TMP_DIR}/${ZIP_NAME}" <<'PYEOF'
import os
import shutil
import sys
import zipfile

pkg_dir, zip_path = sys.argv[1], sys.argv[2]

# Walk bottom-up so parent dirs are processed after children
for dirpath, dirnames, filenames in os.walk(pkg_dir, topdown=False):
    for d in dirnames:
        full = os.path.join(dirpath, d)
        if d in ("__pycache__", "tests", "test"):
            shutil.rmtree(full)
    for f in filenames:
        if f.endswith((".pyc", ".pyo")):
            os.remove(os.path.join(dirpath, f))

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for dirpath, _, filenames in os.walk(pkg_dir):
        for f in filenames:
            full = os.path.join(dirpath, f)
            zf.write(full, os.path.relpath(full, os.path.dirname(pkg_dir)))
PYEOF

mv "${TMP_DIR}/${ZIP_NAME}" "${ZIP_PATH}"
echo "${ZIP_PATH}"
