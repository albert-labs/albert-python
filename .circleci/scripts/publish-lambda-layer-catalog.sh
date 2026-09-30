#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: .circleci/scripts/publish-lambda-layer-catalog.sh --file <catalog.json> [--dest <path>] [--remote <name>]

Commits the Lambda layer catalog to the gh-pages branch so the docs site serves it at
https://docs.developer.albertinvent.com/albert-python/lambda-layers.json.
The file sits outside mike's version directories, so docs deploys leave it alone.
Retries when a concurrent docs deploy moves gh-pages. Does nothing if the file is unchanged.
EOF
}

FILE=""
DEST="albert-python/lambda-layers.json"
REMOTE="origin"
BRANCH="gh-pages"
ATTEMPTS=5

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file)
      FILE="$2"
      shift 2
      ;;
    --dest)
      DEST="$2"
      shift 2
      ;;
    --remote)
      REMOTE="$2"
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

if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "Catalog file not found: ${FILE:-<missing --file>}" >&2
  exit 1
fi
FILE="$(cd "$(dirname "$FILE")" && pwd)/$(basename "$FILE")"

WORKTREE="$(mktemp -d)"
cleanup() {
  git worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
}
trap cleanup EXIT

git fetch --quiet "$REMOTE" "$BRANCH"
git worktree add --quiet --detach "$WORKTREE" FETCH_HEAD

for attempt in $(seq 1 "$ATTEMPTS"); do
  git -C "$WORKTREE" fetch --quiet "$REMOTE" "$BRANCH"
  git -C "$WORKTREE" reset --quiet --hard FETCH_HEAD

  # generated_at changes on every run; only publish when the layer list itself changed.
  if [[ -f "$WORKTREE/$DEST" ]] && python3 - "$WORKTREE/$DEST" "$FILE" <<'EOF'
import json, sys
old, new = (json.load(open(path)) for path in sys.argv[1:])
sys.exit(0 if old.get("layers") == new.get("layers") else 1)
EOF
  then
    echo "Lambda layer catalog on ${BRANCH} is already up to date."
    exit 0
  fi

  mkdir -p "$WORKTREE/$(dirname "$DEST")"
  cp "$FILE" "$WORKTREE/$DEST"
  git -C "$WORKTREE" add "$DEST"
  git -C "$WORKTREE" commit --quiet -m "Update Lambda layer catalog"
  if git -C "$WORKTREE" push --quiet "$REMOTE" "HEAD:${BRANCH}"; then
    echo "Published Lambda layer catalog to ${BRANCH}:${DEST}"
    exit 0
  fi

  echo "Push to ${BRANCH} was rejected (attempt ${attempt}/${ATTEMPTS}); retrying." >&2
  sleep $((attempt * 5))
done

echo "Could not publish the Lambda layer catalog after ${ATTEMPTS} attempts." >&2
exit 1
