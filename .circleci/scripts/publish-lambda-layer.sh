#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: .circleci/scripts/publish-lambda-layer.sh --zip <path> --regions <region[,region...]> --runtime <3.12> --arch <x86_64|arm64> --sdk-version <x.y.z> [--account-id <aws_account_id>] [--no-public] [--manifest <path>]

Publishes a Lambda layer version from a local zip file using direct upload, once per region.
Skips publishing in a region that already has a layer version for this SDK version.
Fails if the zip exceeds 50 MB.

--manifest appends one tab-separated line per region to <path>:
  <region> <runtime> <arch> <layer_arn> <published|reused>
EOF
}

ZIP_PATH=""
REGIONS=""
RUNTIME=""
ARCH=""
SDK_VERSION=""
MAKE_PUBLIC="1"
ACCOUNT_ID=""
MANIFEST_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --zip)
      ZIP_PATH="$2"
      shift 2
      ;;
    --regions)
      REGIONS="$2"
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
    --manifest)
      MANIFEST_PATH="$2"
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

if [[ -z "$ZIP_PATH" || -z "$REGIONS" || -z "$RUNTIME" || -z "$ARCH" || -z "$SDK_VERSION" ]]; then
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
LAYER_NAME="albert-python-py${RUNTIME_NO_DOT}-${ARCH}"
# The prefix is what the idempotency check matches on; keep it stable.
DESCRIPTION_PREFIX="albert-python ${SDK_VERSION} |"
DESCRIPTION="${DESCRIPTION_PREFIX} python${RUNTIME} | ${ARCH} | ${BUILD_DATE} | sha=${GIT_SHA}"

# Walks every page of list-layer-versions (the API returns at most 50 per call)
# and prints the ARN of the first version whose description carries this SDK
# version, or nothing if none exists. Newest versions are returned first.
find_existing_layer_arn() {
  local region="$1"
  local marker="" page="" arn="" next=""
  local -a marker_args=()

  while :; do
    marker_args=()
    if [[ -n "${marker}" ]]; then
      marker_args=(--marker "${marker}")
    fi
    # errexit does not apply inside command substitutions, so check explicitly:
    # a failed lookup must abort rather than fall through to a publish.
    if ! page="$(
      aws lambda list-layer-versions \
        --region "${region}" \
        --layer-name "${LAYER_NAME}" \
        --no-paginate \
        ${marker_args[@]+"${marker_args[@]}"} \
        --query "[LayerVersions[?starts_with(Description, '${DESCRIPTION_PREFIX}')].LayerVersionArn | [0], NextMarker]" \
        --output text
    )"; then
      echo "Failed to list versions of ${LAYER_NAME} in ${region}." >&2
      return 1
    fi
    IFS=$'\t' read -r arn next <<<"${page}"
    if [[ -n "${arn}" && "${arn}" != "None" ]]; then
      echo "${arn}"
      return 0
    fi
    if [[ -z "${next}" || "${next}" == "None" ]]; then
      return 0
    fi
    marker="${next}"
  done
}

# Grants lambda:GetLayerVersion on one layer version to everyone, or to --account-id
# when set. Permissions are per version. An existing statement counts as success.
grant_layer_access() {
  local region="$1" version="$2"
  local principal='*' statement_id='public-access' err=""

  if [[ -n "$ACCOUNT_ID" ]]; then
    principal="$ACCOUNT_ID"
    statement_id="allow-account-${ACCOUNT_ID}"
  fi

  if err="$(
    aws lambda add-layer-version-permission \
      --region "${region}" \
      --layer-name "${LAYER_NAME}" \
      --version-number "${version}" \
      --statement-id "${statement_id}" \
      --action lambda:GetLayerVersion \
      --principal "${principal}" \
      --output text 2>&1 >/dev/null
  )"; then
    echo "Granted lambda:GetLayerVersion on version ${version} to ${principal}."
  elif [[ "${err}" == *ResourceConflictException* ]]; then
    echo "Permission '${statement_id}' already present on version ${version}."
  else
    echo "Failed to grant access on ${LAYER_NAME}:${version} in ${region}: ${err}" >&2
    return 1
  fi
}

IFS=',' read -ra REGION_LIST <<<"${REGIONS}"

if [[ -n "${MANIFEST_PATH}" ]]; then
  mkdir -p "$(dirname "${MANIFEST_PATH}")"
fi

for REGION in "${REGION_LIST[@]}"; do
  REGION="${REGION// /}"
  [[ -z "$REGION" ]] && continue
  echo "== ${REGION}: ${LAYER_NAME}"

  # Idempotent: if a layer version for this SDK version already exists, reuse it.
  EXISTING_ARN="$(find_existing_layer_arn "${REGION}")"
  STATUS="published"

  if [[ -n "${EXISTING_ARN}" ]]; then
    LAYER_ARN="${EXISTING_ARN}"
    LAYER_VERSION="${LAYER_ARN##*:}"
    STATUS="reused"
    echo "Layer version ${LAYER_VERSION} already contains albert-python ${SDK_VERSION}; skipping publish."
  else
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

    echo "Published layer version ${LAYER_VERSION}"
  fi

  # Runs for reused versions too, so a version left private by an earlier run is repaired.
  if [[ "$MAKE_PUBLIC" == "1" ]]; then
    grant_layer_access "${REGION}" "${LAYER_VERSION}"
  fi

  echo "Layer ARN: ${LAYER_ARN}"

  if [[ -n "${MANIFEST_PATH}" ]]; then
    printf '%s\t%s\t%s\t%s\t%s\n' \
      "${REGION}" "${RUNTIME}" "${ARCH}" "${LAYER_ARN}" "${STATUS}" >>"${MANIFEST_PATH}"
  fi
done
