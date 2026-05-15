#!/usr/bin/env bash
# =============================================================================
# Inferflow MLOps — end-to-end demo
#
# Prerequisites:
#   • Docker Compose stack running:  docker compose up -d
#   • jq installed:                  brew install jq  /  apt install jq
#
# Usage:
#   bash scripts/demo.sh [--base-url http://localhost:8000] [--audio-url URL]
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults (overridable via flags)
# ---------------------------------------------------------------------------
BASE_URL="http://localhost:8000"
AUDIO_URL="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
USERNAME="admin"
PASSWORD="demo-password"
MAX_WAIT=120   # seconds to wait for job completion
POLL_INTERVAL=3

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)  BASE_URL="$2";  shift 2 ;;
    --audio-url) AUDIO_URL="$2"; shift 2 ;;
    *)           echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

log()   { printf "${BOLD}==> %s${RESET}\n" "$*"; }
ok()    { printf "${GREEN}    ✓ %s${RESET}\n" "$*"; }
warn()  { printf "${YELLOW}    ⚠ %s${RESET}\n" "$*"; }
die()   { printf "${RED}    ✗ %s${RESET}\n" "$*" >&2; exit 1; }

require_cmd() { command -v "$1" >/dev/null 2>&1 || die "'$1' is required but not found. Install it first."; }

require_cmd curl
require_cmd jq

# ---------------------------------------------------------------------------
# 1. Liveness check
# ---------------------------------------------------------------------------
log "Checking liveness — GET $BASE_URL/health"
HEALTH=$(curl -sf "$BASE_URL/health") || die "Service not reachable. Is the stack running? (docker compose up -d)"
STATUS=$(echo "$HEALTH" | jq -r '.status')
[[ "$STATUS" == "ok" ]] || die "Unexpected health status: $STATUS"
ok "Service healthy (uptime: $(echo "$HEALTH" | jq -r '.uptime_seconds')s)"

# ---------------------------------------------------------------------------
# 2. Readiness check
# ---------------------------------------------------------------------------
log "Checking readiness — GET $BASE_URL/ready"
READY=$(curl -sf "$BASE_URL/ready") || die "Readiness endpoint unreachable"
READY_STATUS=$(echo "$READY" | jq -r '.status')
[[ "$READY_STATUS" == "ready" ]] || warn "Readiness: $READY_STATUS — continuing anyway"
REDIS_STATUS=$(echo "$READY" | jq -r '.checks.redis.status')
QDRANT_STATUS=$(echo "$READY" | jq -r '.checks.qdrant.status')
ok "Redis: $REDIS_STATUS | Qdrant: $QDRANT_STATUS"

# ---------------------------------------------------------------------------
# 3. Login
# ---------------------------------------------------------------------------
log "Authenticating — POST $BASE_URL/auth/token"
AUTH_RESP=$(curl -sf -X POST "$BASE_URL/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}") \
  || die "Login failed"
TOKEN=$(echo "$AUTH_RESP" | jq -r '.access_token')
[[ -n "$TOKEN" && "$TOKEN" != "null" ]] || die "No token in response"
ok "Token acquired (${#TOKEN} chars)"

# ---------------------------------------------------------------------------
# 4. Submit transcription job
# ---------------------------------------------------------------------------
log "Submitting transcription job"
printf "    Audio URL: %s\n" "$AUDIO_URL"
JOB_RESP=$(curl -sf -X POST "$BASE_URL/transcribe" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"audio_url\": \"$AUDIO_URL\", \"language\": \"en\"}") \
  || die "Failed to submit transcription job"
JOB_ID=$(echo "$JOB_RESP" | jq -r '.job_id')
[[ -n "$JOB_ID" && "$JOB_ID" != "null" ]] || die "No job_id in response"
ok "Job created: $JOB_ID"

# ---------------------------------------------------------------------------
# 5. Poll until complete (or timeout)
# ---------------------------------------------------------------------------
log "Waiting for job completion (max ${MAX_WAIT}s, polling every ${POLL_INTERVAL}s)"
ELAPSED=0
STATUS="pending"
while [[ "$STATUS" == "pending" || "$STATUS" == "processing" ]]; do
  sleep "$POLL_INTERVAL"
  ELAPSED=$((ELAPSED + POLL_INTERVAL))
  JOB_DATA=$(curl -sf "$BASE_URL/jobs/$JOB_ID" \
    -H "Authorization: Bearer $TOKEN") \
    || die "Failed to poll job status"
  STATUS=$(echo "$JOB_DATA" | jq -r '.status')
  printf "    [%3ds] status: %s\n" "$ELAPSED" "$STATUS"
  if [[ "$ELAPSED" -ge "$MAX_WAIT" ]]; then
    die "Job did not complete within ${MAX_WAIT}s. Last status: $STATUS"
  fi
done

[[ "$STATUS" == "completed" ]] || die "Job ended with status: $STATUS"
TRANSCRIPT=$(echo "$JOB_DATA" | jq -r '.result.transcript // "(empty)"')
LANGUAGE=$(echo "$JOB_DATA" | jq -r '.result.language // "?"')
DURATION=$(echo "$JOB_DATA" | jq -r '.result.duration // "?"')
ok "Job completed in ${ELAPSED}s — language: $LANGUAGE, duration: ${DURATION}s"
printf "\n${BOLD}Transcript preview:${RESET}\n"
echo "$TRANSCRIPT" | head -5 | sed 's/^/    /'
echo

# ---------------------------------------------------------------------------
# 6. Semantic search
# ---------------------------------------------------------------------------
log "Semantic search — POST $BASE_URL/search"
SEARCH_QUERY="audio music"
SEARCH_RESP=$(curl -sf -X POST "$BASE_URL/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"$SEARCH_QUERY\", \"limit\": 3}") \
  || die "Search request failed"
TOTAL=$(echo "$SEARCH_RESP" | jq -r '.total')
ok "Search returned $TOTAL result(s) for query: \"$SEARCH_QUERY\""
if [[ "$TOTAL" -gt 0 ]]; then
  echo "$SEARCH_RESP" | jq -r '.results[] | "    score=\(.score|tostring[:6])  job=\(.job_id)  lang=\(.language)"'
fi

echo
printf "${GREEN}${BOLD}Demo completed successfully!${RESET}\n"
