#!/usr/bin/env python3
"""Live development server for docs/.

Serves the built site, watches src/ and content/, rebuilds on every save, and
pushes the result straight to any page you have open:

  * a .css save is swapped in place — no reload, so your scroll position and
    any half-open fold stay exactly as they were
  * anything else reloads the page, restoring the scroll position
  * a build error shows up as a banner on the page (and in this terminal)
    instead of silently serving stale HTML

    python3 src/dev_server.py [--port 8000] [--host 127.0.0.1]

Normally you want ./serve.sh, which starts this and opens a browser.
Nothing here touches docs/ except by running the ordinary build, and the
live-reload snippet is injected on the way out — never written to disk.
"""
import argparse
import http.server
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
WATCH = [ROOT / "src", ROOT / "content"]
SKIP_DIRS = {"__pycache__", "node_modules", ".git", ".idea", ".venv"}
# editor scratch: JetBrains writes <name>___jb_tmp___ then renames over the target,
# and vim/sed leave .swp/.bak behind. Watching those means spurious rebuilds and a
# stray .bak turning a stylesheet save into a full page reload.
SKIP_SUFFIXES = (".pyc", ".bak", ".orig", ".rej", ".tmp", ".swp", ".swx", ".swo", "~")
SKIP_MARKERS = ("___jb_",)
BUILDS = [["src/build.py"], ["src/blog/build.py"]]
POLL = 0.25      # seconds between directory scans
SETTLE = 0.15    # wait for writes to stop before building
PING = 15        # seconds between keep-alive comments on an idle stream

clients = []
clients_lock = threading.Lock()

LIVE_JS = """
(function () {
    var KEY = "__dev_scroll";
    try {
        var y = sessionStorage.getItem(KEY);
        if (y !== null) { sessionStorage.removeItem(KEY); addEventListener("load", function () { scrollTo(0, +y); }); }
    } catch (e) {}

    var banner = null;
    function show(text) {
        if (!banner) {
            banner = document.createElement("pre");
            banner.style.cssText = "position:fixed;z-index:2147483647;left:0;right:0;bottom:0;margin:0;" +
                "max-height:45vh;overflow:auto;padding:14px 18px;background:#2b2118;color:#ffd9c8;" +
                "font:12px/1.5 ui-monospace,Menlo,monospace;white-space:pre-wrap;" +
                "box-shadow:0 -2px 18px rgba(0,0,0,.35)";
            document.body.appendChild(banner);
        }
        banner.textContent = text;
        banner.scrollTop = banner.scrollHeight;
    }
    function clear() { if (banner) { banner.remove(); banner = null; } }

    function reload() {
        try { sessionStorage.setItem(KEY, String(scrollY)); } catch (e) {}
        location.reload();
    }

    // Re-request every stylesheet under a fresh query, swapping each link only
    // once its replacement has loaded so the page never flashes unstyled.
    function swapCss() {
        document.querySelectorAll("link[rel=stylesheet]").forEach(function (link) {
            var url = new URL(link.getAttribute("href"), location.href);
            if (url.origin !== location.origin) return;
            url.searchParams.set("__dev", Date.now());
            var next = link.cloneNode();
            next.href = url.pathname + url.search;
            next.addEventListener("load", function () {
                link.remove();
                // Some scripts read CSS custom properties as settings (fold.js does);
                // nudge them to look again now the new sheet is live.
                dispatchEvent(new Event("resize"));
            }, { once: true });
            next.addEventListener("error", function () { next.remove(); }, { once: true });
            link.after(next);
        });
    }

    function connect() {
        var es = new EventSource("/__live");
        es.onmessage = function (e) {
            var m = JSON.parse(e.data);
            if (m.type === "reload") reload();
            else if (m.type === "css") { clear(); swapCss(); }
            else if (m.type === "error") show(m.text);
            else if (m.type === "ok") clear();
        };
        es.onerror = function () { es.close(); setTimeout(connect, 700); };
    }
    connect();
})();
"""
SNIPPET = ("<script>" + LIVE_JS + "</script>\n").encode()


def broadcast(message):
    with clients_lock:
        for q in clients:
            q.put(message)


def scan():
    """mtime of every source file we care about, keyed by path."""
    seen = {}
    for root in WATCH:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for name in filenames:
                if (name.startswith(".") or name.endswith(SKIP_SUFFIXES)
                        or any(mark in name for mark in SKIP_MARKERS)):
                    continue
                path = Path(dirpath) / name
                try:
                    seen[path] = path.stat().st_mtime_ns
                except OSError:
                    pass
    return seen


def build():
    """Run the ordinary build. Returns None, or the output of the step that failed."""
    for script in BUILDS:
        done = subprocess.run([sys.executable, *script], cwd=ROOT, capture_output=True, text=True)
        if done.returncode:
            return (done.stdout + done.stderr).strip() or f"{script[0]} exited {done.returncode}"
        sys.stdout.write(done.stdout)
    sys.stdout.flush()
    return None


def watch():
    before = scan()
    while True:
        time.sleep(POLL)
        after = scan()
        changed = {p for p in set(before) | set(after) if before.get(p) != after.get(p)}
        if not changed:
            continue

        # let a burst of saves finish before building
        while True:
            time.sleep(SETTLE)
            settled = scan()
            if settled == after:
                break
            changed |= {p for p in set(after) | set(settled) if after.get(p) != settled.get(p)}
            after = settled
        before = after

        names = ", ".join(sorted(p.relative_to(ROOT).as_posix() for p in changed)[:4])
        extra = f" (+{len(changed) - 4} more)" if len(changed) > 4 else ""
        print(f"\n› {names}{extra}", flush=True)

        error = build()
        if error:
            print(error, file=sys.stderr, flush=True)
            broadcast({"type": "error", "text": error})
            continue

        # A stylesheet on its own can be swapped in place; anything else may have
        # changed the markup, so the page has to come back.
        css_only = all(p.suffix == ".css" for p in changed)
        broadcast({"type": "ok"})
        broadcast({"type": "css" if css_only else "reload"})
        print("  → " + ("styles swapped" if css_only else "reloaded"), flush=True)


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        # A browser walking away mid-response (a reload, a closed tab, an event
        # stream we no longer serve) is normal here, not worth a traceback.
        if not isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
            super().handle_error(request, client_address)


class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def do_GET(self):
        clean = self.path.split("?", 1)[0].split("#", 1)[0]
        if clean == "/__live":
            return self.stream()

        target = Path(self.translate_path(self.path))
        if target.is_dir() and clean.endswith("/"):
            target = target / "index.html"
        if target.suffix == ".html" and target.is_file():
            return self.send_html(target)
        return super().do_GET()

    def send_html(self, target):
        body = target.read_bytes()
        if b"</body>" in body:
            body = body.replace(b"</body>", SNIPPET + b"</body>", 1)
        else:
            body += SNIPPET
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def stream(self):
        q = queue.Queue()
        with clients_lock:
            clients.append(q)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.close_connection = True  # no Content-Length: the body ends with the socket
            self.end_headers()
            while True:
                try:
                    message = q.get(timeout=PING)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                else:
                    self.wfile.write(b"data: " + json.dumps(message).encode() + b"\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with clients_lock:
                if q in clients:
                    clients.remove(q)

    def log_message(self, fmt, *args):
        pass  # the build output is the interesting part; requests are noise


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    print("› building", flush=True)
    error = build()
    if error:
        print(error, file=sys.stderr)
        return 1

    threading.Thread(target=watch, daemon=True).start()

    server = Server((args.host, args.port), Handler)
    print(f"› live at http://{args.host}:{args.port}/  — watching src/ and content/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
