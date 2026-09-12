#!/usr/bin/env bash
# Live development server: builds the whole site (resume + blog), serves docs/,
# and rebuilds on every save under src/ or content/, pushing the result to any
# page you have open. A .css save is swapped in place without reloading, so your
# scroll position and any half-open fold survive; anything else reloads the page.
# Build errors appear as a banner on the page as well as here.
#
#   ./serve.sh                      -> http://127.0.0.1:8000/
#   ./serve.sh blog/flatminima/     -> opens that page instead of the homepage
#   PORT=9000 ./serve.sh            -> pick another port
#   ./serve.sh --no-open [path]     -> serve without launching a browser
#
# Ctrl+C stops it. The watcher lives in src/dev_server.py.
set -euo pipefail
cd "$(dirname "$0")"

open_browser=1
if [[ "${1:-}" == "--no-open" ]]; then open_browser=0; shift; fi
page="${1:-}"
port="${PORT:-8000}"
url="http://127.0.0.1:${port}/${page#/}"

python3 src/dev_server.py --port "${port}" &
server=$!
trap 'kill "${server}" 2>/dev/null' EXIT INT TERM

# wait for the port to come up before opening it
for _ in $(seq 1 100); do
    curl -s -o /dev/null "${url}" && break
    sleep 0.1
done

if (( open_browser )); then
    if command -v open > /dev/null; then open "${url}"
    elif command -v xdg-open > /dev/null; then xdg-open "${url}"
    else echo "  open ${url} in your browser"
    fi
fi

echo "› Ctrl+C to stop"
wait "${server}"
