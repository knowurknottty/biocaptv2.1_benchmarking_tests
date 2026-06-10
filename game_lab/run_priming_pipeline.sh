#!/usr/bin/env bash
# End-to-end priming pipeline: local self-play at scale against the REAL
# sealed binaries, then export primed memory seeds for the worker deploy.
#
# Run on a machine that has the local WASM bundle (default
# ~/2clean4u/CAPTLang_WASM/versions/2.1). From game_lab/:
#
#   ./run_priming_pipeline.sh                 # 25000 games per game type (50k total)
#   GAMES=500 ./run_priming_pipeline.sh       # smaller run
#   MOCK=1 GAMES=10 ./run_priming_pipeline.sh # pipeline validation, no binaries
#
# Steps: prepare wasm -> start local v1 server -> self-play checkers+chess in
# parallel -> verify memory-bank chains -> export primed seeds into the worker
# package. Banks are append-only: rerunning RESUMES on top of existing memory.
# Afterwards: cd $WORKER_DIR && npm run deploy
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKER_DIR="${WORKER_DIR:-$HERE/../../capt-functional-context-public/cloudflare/capt-wasm-worker}"
GAMES="${GAMES:-25000}"
PRODUCT="${PRODUCT:-biocapt}"
PORT="${LOCAL_WASM_PORT:-8787}"
MOCK="${MOCK:-0}"
SEED_POSITIONS="${SEED_POSITIONS:-512}"

cd "$WORKER_DIR"
SERVER_ARGS=()
if [ "$MOCK" = "1" ]; then
  SERVER_ARGS+=(--mock)
else
  npm run prepare:wasm
fi

LOCAL_WASM_PORT="$PORT" node scripts/local-server.mjs "${SERVER_ARGS[@]+"${SERVER_ARGS[@]}"}" &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 50); do
  if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then break; fi
  sleep 0.2
done
curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || { echo "local server failed to start"; exit 1; }
echo "local v1 server up on port $PORT (mock=$MOCK)"

cd "$HERE"
URL="http://127.0.0.1:$PORT"
# separate banks for real and mock lineages so they can never mix
BANK_LABEL=$([ "$MOCK" = "1" ] && echo "${PRODUCT}_mocklocal" || echo "${PRODUCT}_local")

run_selfplay() {
  python3 selfplay_arena.py --game "$1" --games "$GAMES" --product "$PRODUCT" \
    --worker-url "$URL" --bank-label "$BANK_LABEL" 2>&1 | sed "s/^/[$1] /"
}
run_selfplay checkers &
CHECKERS_PID=$!
run_selfplay chess &
CHESS_PID=$!
wait "$CHECKERS_PID" "$CHESS_PID"

python3 export_primed_seed.py --game checkers --product "$PRODUCT" \
  --bank-label "$BANK_LABEL" --positions "$SEED_POSITIONS"
python3 export_primed_seed.py --game chess --product "$PRODUCT" \
  --bank-label "$BANK_LABEL" --positions "$SEED_POSITIONS"

echo
echo "PIPELINE COMPLETE. Primed seeds written into $WORKER_DIR/primed/primed-seeds.json"
echo "Deploy the primed worker with:"
echo "  cd $WORKER_DIR && npm test && npm run deploy"
