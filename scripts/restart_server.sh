#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"
DB="${CCM_DB:-$HOME/.cc-session-manager/index.sqlite}"
PID_FILE="$ROOT_DIR/.sessionview-server.pid"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/server.log"
BUILD_WEB="${BUILD_WEB:-1}"

cd "$ROOT_DIR"
mkdir -p "$LOG_DIR"

stop_pid() {
  local pid="$1"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "Stopping existing SessionView server: $pid"
    kill "$pid" 2>/dev/null || true
    for _ in {1..30}; do
      if ! kill -0 "$pid" 2>/dev/null; then
        return
      fi
      sleep 0.1
    done
    kill -9 "$pid" 2>/dev/null || true
  fi
}

if [[ -f "$PID_FILE" ]]; then
  stop_pid "$(cat "$PID_FILE")"
fi

existing_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
if [[ -n "$existing_pid" ]]; then
  stop_pid "$existing_pid"
fi

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
  echo "Missing .venv. Create it first:"
  echo "  python3 -m venv .venv && . .venv/bin/activate && python -m pip install -e '.[dev]'"
  exit 1
fi

if [[ "$BUILD_WEB" == "1" ]]; then
  echo "Building web UI..."
  (cd "$ROOT_DIR/web" && npm install >/dev/null && npm run build)
fi

echo "Starting SessionView at http://$HOST:$PORT"
echo "DB: $DB"
echo "Log: $LOG_FILE"

export CCM_DB="$DB"
if command -v setsid >/dev/null 2>&1; then
  setsid "$ROOT_DIR/.venv/bin/python" -m uvicorn "ccm.api:create_app" --factory --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 </dev/null &
else
  nohup "$ROOT_DIR/.venv/bin/python" -m uvicorn "ccm.api:create_app" --factory --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 </dev/null &
fi
pid="$!"
echo "$pid" > "$PID_FILE"

for _ in {1..50}; do
  if curl -fsS "http://$HOST:$PORT/api/health" >/dev/null 2>&1; then
    echo "SessionView restarted. PID: $pid"
    disown "$pid" 2>/dev/null || true
    exit 0
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "Server exited during startup. Recent log:"
    tail -80 "$LOG_FILE"
    exit 1
  fi
  sleep 0.1
done

echo "Server did not become healthy in time. Recent log:"
tail -80 "$LOG_FILE"
exit 1
