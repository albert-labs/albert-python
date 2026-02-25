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

docker run \
  --rm \
  --platform "${PLATFORM}" \
  --entrypoint /bin/bash \
  --user "$(id -u):$(id -g)" \
  -v "${TMP_DIR}:/work" \
  "${IMAGE}" \
  -lc "\
    set -euo pipefail; \
    python -m pip install --no-cache-dir --only-binary numpy,pandas albert==${SDK_VERSION} -t /work/python; \
    PYTHONPATH=/work/python python -c 'import albert'; \
    find /work/python -name '__pycache__' -type d -prune -exec rm -rf {} +; \
    find /work/python -name '*.pyc' -o -name '*.pyo' | xargs -r rm -f; \
    find /work/python -path '*/tests/*' -type f -delete; \
    python -c \"import os, zipfile; \
z = zipfile.ZipFile('/work/${ZIP_NAME}', 'w', zipfile.ZIP_DEFLATED); \
[(z.write(os.path.join(root, name), os.path.relpath(os.path.join(root, name), '/work'))) \
for root, _, files in os.walk('/work/python') for name in files]; \
z.close()\" \
  " 1>&2

mv "${TMP_DIR}/${ZIP_NAME}" "${ZIP_PATH}"
echo "${ZIP_PATH}"
