#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: .circleci/scripts/publish-lambda-layer.sh --zip <path> --region <aws_region> --runtime <3.12> --arch <x86_64|arm64> --sdk-version <x.y.z> [--account-id <aws_account_id>] [--no-public]

Publishes a Lambda layer version from a local zip file using direct upload.
Fails if the zip exceeds 50 MB.
EOF
}

ZIP_PATH=""
REGION=""
RUNTIME=""
ARCH=""
SDK_VERSION=""
MAKE_PUBLIC="1"
ACCOUNT_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --zip)
      ZIP_PATH="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
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
    --sdk-version)
      SDK_VERSION="$2"
      shift 2
      ;;
    --account-id)
      ACCOUNT_ID="$2"
      shift 2
      ;;
    --no-public)
      MAKE_PUBLIC="0"
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

if [[ -z "$ZIP_PATH" || -z "$REGION" || -z "$RUNTIME" || -z "$ARCH" || -z "$SDK_VERSION" ]]; then
  echo "Missing required arguments." >&2
  usage
  exit 1
fi

if [[ ! -f "$ZIP_PATH" ]]; then
  echo "Zip not found: $ZIP_PATH" >&2
  exit 1
fi

if [[ "$ARCH" != "x86_64" && "$ARCH" != "arm64" ]]; then
  echo "Invalid --arch. Expected x86_64 or arm64." >&2
  exit 1
fi

if [[ -n "$ACCOUNT_ID" && ! "$ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
  echo "Invalid --account-id. Expected a 12-digit AWS account ID." >&2
  exit 1
fi

if [[ "$MAKE_PUBLIC" == "0" && -n "$ACCOUNT_ID" ]]; then
  echo "--no-public cannot be used with --account-id." >&2
  exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required but not installed." >&2
  exit 1
fi

ZIP_SIZE_BYTES=""
if ZIP_SIZE_BYTES=$(stat -f%z "$ZIP_PATH" 2>/dev/null); then
  :
elif ZIP_SIZE_BYTES=$(stat -c%s "$ZIP_PATH" 2>/dev/null); then
  :
else
  echo "Unable to determine zip size." >&2
  exit 1
fi

MAX_BYTES=$((50 * 1024 * 1024))
if (( ZIP_SIZE_BYTES > MAX_BYTES )); then
  echo "Zip exceeds 50 MB direct upload limit: ${ZIP_SIZE_BYTES} bytes" >&2
  exit 1
fi

GIT_SHA="${GIT_SHA:-}"
if [[ -z "$GIT_SHA" ]]; then
  if command -v git >/dev/null 2>&1; then
    GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || true)"
  fi
fi
GIT_SHA="${GIT_SHA:-unknown}"

BUILD_DATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

RUNTIME_NO_DOT="${RUNTIME//./}"
LAYER_NAME="albert-python-sdk-py${RUNTIME_NO_DOT}-${ARCH}"
DESCRIPTION="Albert SDK v${SDK_VERSION} | ${ARCH} | ${BUILD_DATE} | sha=${GIT_SHA}"

PUBLISH_OUTPUT=""
PUBLISH_OUTPUT="$(
  aws lambda publish-layer-version \
    --region "${REGION}" \
    --layer-name "${LAYER_NAME}" \
    --description "${DESCRIPTION}" \
    --compatible-runtimes "python${RUNTIME}" \
    --compatible-architectures "${ARCH}" \
    --zip-file "fileb://${ZIP_PATH}" \
    --query '[LayerVersionArn,Version]' \
    --output text
)"

read -r LAYER_ARN LAYER_VERSION <<<"${PUBLISH_OUTPUT}"

if [[ -z "${LAYER_ARN:-}" || -z "${LAYER_VERSION:-}" ]]; then
  echo "Failed to publish layer or parse publish response." >&2
  exit 1
fi

if [[ "$MAKE_PUBLIC" == "1" ]]; then
  PRINCIPAL='*'
  STATEMENT_ID='public-access'
  if [[ -n "$ACCOUNT_ID" ]]; then
    PRINCIPAL="$ACCOUNT_ID"
    STATEMENT_ID="allow-account-${ACCOUNT_ID}"
  fi

  aws lambda add-layer-version-permission \
    --region "${REGION}" \
    --layer-name "${LAYER_NAME}" \
    --version-number "${LAYER_VERSION}" \
    --statement-id "${STATEMENT_ID}" \
    --action lambda:GetLayerVersion \
    --principal "${PRINCIPAL}"
fi

echo "Published layer version ${LAYER_VERSION}"
echo "Layer ARN: ${LAYER_ARN}"
