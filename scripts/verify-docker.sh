#!/usr/bin/env bash
# =====================================================================
# Smart Greenhouse — Docker Compose verification script
# =====================================================================
# Run this on a machine with Docker Hub access (or any reachable
# container registry) to verify the Compose stack end to end.
#
#   ./scripts/verify-docker.sh
#
# The script tears the stack down at the end (Ctrl-C also tears down).

set -euo pipefail

cd "$(dirname "$0")/.."

# Colours (optional, no-op if NO_COLOR is set).
if [[ -z "${NO_COLOR:-}" ]]; then
  GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; BLUE=$'\033[0;34m'; NC=$'\033[0m'
else
  GREEN=; RED=; BLUE=; NC=
fi

step() { printf "\n${BLUE}== %s ==${NC}\n" "$1"; }
ok()   { printf "${GREEN}OK${NC}  %s\n" "$1"; }
fail() { printf "${RED}FAIL${NC} %s\n" "$1"; exit 1; }

cleanup() {
  step "Tearing down"
  docker compose down --remove-orphans || true
}
trap cleanup EXIT

# ---------------------------------------------------------------------
step "1. docker compose build"
docker compose build

step "2. docker compose up -d"
docker compose up -d

step "3. Waiting for backend health (max 60s)"
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/api/health > /dev/null; then
    ok "backend responded after ${i}s"
    break
  fi
  if [[ "$i" -eq 60 ]]; then
    fail "backend never became healthy"
  fi
  sleep 1
done

step "4. GET /api/health"
HEALTH=$(curl -s http://localhost:8000/api/health)
echo "$HEALTH"
echo "$HEALTH" | grep -q '"status":"ok"' && ok "status ok" || fail "unexpected health body"

step "5. Wait 10s for the simulator to push readings"
sleep 10

step "6. GET /api/readings/latest"
LATEST=$(curl -s http://localhost:8000/api/readings/latest)
echo "$LATEST"
echo "$LATEST" | grep -q '"temperature"' && ok "temperature present" || fail "no temperature reading yet"
echo "$LATEST" | grep -q '"humidity"' && ok "humidity present" || fail "no humidity reading yet"
echo "$LATEST" | grep -q '"soil_moisture"' && ok "soil_moisture present" || fail "no soil_moisture reading yet"
echo "$LATEST" | grep -q '"light"' && ok "light present" || fail "no light reading yet"

step "7. GET frontend (should return HTML)"
FRONT=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/)
[[ "$FRONT" == "200" ]] && ok "frontend HTTP 200" || fail "frontend returned $FRONT"

step "8. GET /healthz (nginx healthcheck endpoint)"
HZ=$(curl -s http://localhost:5173/healthz)
[[ "$HZ" == "ok" ]] && ok "nginx healthcheck reports ok" || fail "nginx healthcheck unexpected body: $HZ"

step "9. docker compose logs simulator (last 10 lines)"
docker compose logs --tail 10 simulator

step "10. docker compose ps"
docker compose ps

printf "\n${GREEN}All Docker runtime checks passed.${NC}\n"
