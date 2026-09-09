#!/usr/bin/env bash
# Rebuild the whole site (resume + blog), serve docs/ locally, and open it.
#
#   ./serve.sh                      -> http://127.0.0.1:8000/
#   ./serve.sh blog/flatminima/     -> opens that page instead of the homepage
#   PORT=9000 ./serve.sh            -> pick another port
#   ./serve.sh --no-open [path]     -> build + serve without launching a browser
#
# Ctrl+C stops the server. Re-run after editing content or src/ to rebuild.
set -euo pipefail
cd "$(dirname "$0")"

open_browser=1
if [[ "${1:-}" == "--no-open" ]]; then open_browser=0; shift; fi
page="${1:-}"
port="${PORT:-8000}"
url="http://127.0.0.1:${port}/${page#/}"

echo "› building"
npm run --silent build

echo "› serving docs/ at ${url}"
python3 -m http.server "${port}" --bind 127.0.0.1 --directory docs > /dev/null 2>&1 &
server=$!
trap 'kill "${server}" 2>/dev/null' EXIT INT TERM

# wait for the port to come up before opening it
for _ in $(seq 1 50); do
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
