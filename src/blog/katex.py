"""Build-time KaTeX rendering: one batched node call for cache misses, committed cache."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_PATH = ROOT / "content/blogposts/.katex-cache.json"
RENDER_SCRIPT = Path(__file__).resolve().parent / "katex_render.mjs"


def _installed_version():
    pkg = ROOT / "node_modules/katex/package.json"
    if pkg.exists():
        return json.loads(pkg.read_text())["version"]
    return None


def _key(tex, display, version):
    return hashlib.sha256(f"{tex}\x1f{display}\x1f{version}".encode()).hexdigest()


def render_all(items):
    """items: list of (tex, display_bool) -> list of html strings, in order."""
    if not items:
        return []
    cache = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}
    version = _installed_version() or cache.get("_version")
    if version is None:
        raise SystemExit("KaTeX: no node_modules/katex and no cache. Run `npm install` first.")

    keys = [_key(tex, display, version) for tex, display in items]
    misses = [i for i, k in enumerate(keys) if k not in cache]

    if misses:
        if shutil.which("node") is None:
            raise SystemExit(
                f"KaTeX: {len(misses)} uncached equation(s) but `node` is not available.\n"
                "Install node + run `npm install`, then rebuild (the cache is committed afterwards)."
            )
        payload = json.dumps([{"tex": items[i][0], "display": items[i][1]} for i in misses])
        proc = subprocess.run(
            ["node", str(RENDER_SCRIPT)], input=payload,
            capture_output=True, text=True, cwd=ROOT,
        )
        if proc.returncode != 0:
            raise SystemExit(f"KaTeX render failed:\n{proc.stderr}")
        result = json.loads(proc.stdout)
        version = result["version"]
        for i, html in zip(misses, result["html"]):
            keys[i] = _key(items[i][0], items[i][1], version)
            cache[keys[i]] = html
        cache["_version"] = version
        CACHE_PATH.write_text(json.dumps(cache, indent=1, sort_keys=True))

    return [cache[k] for k in keys]
