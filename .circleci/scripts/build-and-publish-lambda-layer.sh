#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: .circleci/scripts/build-and-publish-lambda-layer.sh --version <sdk_version> --runtime <3.12> --arch <x86_64|arm64> --region <aws_region> [--account-id <aws_account_id>] [--no-public]

Builds a Lambda layer zip and publishes it in one step.
EOF
}

SDK_VERSION=""
RUNTIME=""
ARCH=""
REGION=""
PUBLISH_PUBLIC_FLAG=""
PUBLISH_ACCOUNT_ID_FLAG=""

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
    --region)
      REGION="$2"
      shift 2
      ;;
    --account-id)
      PUBLISH_ACCOUNT_ID_FLAG="--account-id $2"
      shift 2
      ;;
    --no-public)
      PUBLISH_PUBLIC_FLAG="--no-public"
      shift
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

if [[ -z "$SDK_VERSION" || -z "$RUNTIME" || -z "$ARCH" || -z "$REGION" ]]; then
  echo "Missing required arguments." >&2
  usage
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

ZIP_PATH="$(
  "${ROOT_DIR}/.circleci/scripts/build-lambda-layer.sh" \
    --version "${SDK_VERSION}" \
    --runtime "${RUNTIME}" \
    --arch "${ARCH}"
)"

echo "Built zip: ${ZIP_PATH}"

"${ROOT_DIR}/.circleci/scripts/publish-lambda-layer.sh" \
  --zip "${ZIP_PATH}" \
  --region "${REGION}" \
  --runtime "${RUNTIME}" \
  --arch "${ARCH}" \
  --sdk-version "${SDK_VERSION}" \
  ${PUBLISH_ACCOUNT_ID_FLAG} \
  ${PUBLISH_PUBLIC_FLAG}
