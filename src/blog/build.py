"""Blog build: content/blogposts/<slug>/{post.json,post.md,...} -> docs/blog/<slug>/.

Runs AFTER (and independently of) the resume build. Never touches docs/index.html
or docs/markers.css.
"""
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bib
import katex
import markers
import parser as dialect

ROOT = Path(__file__).resolve().parents[2]
BLOG_SRC = Path(__file__).resolve().parent
CONTENT = ROOT / "content/blogposts"
OUT = ROOT / "docs/blog"

MARKER_SYNTAX = re.compile(r"\*\*\*?\{c[1-5]\}\(")


def check_resume_blog_entries():
    """Marker syntax in the homepage blog list would shift the resume's seeded marker
    styles (one random stream, document order). Fail loudly instead."""
    resume = json.loads((ROOT / "content/resume.json").read_text())
    for entry in resume.get("blog", []):
        for value in entry.values():
            if MARKER_SYNTAX.search(value):
                raise SystemExit(
                    f"resume.json blog entry contains marker syntax ({value!r}); "
                    "this would change the resume's marker styling. Remove it."
                )
    return resume


def build_post(post_dir, author, template):
    meta = json.loads((post_dir / "post.json").read_text())
    slug = meta["slug"]
    md = (post_dir / "post.md").read_text()

    bib_entries = {}
    if "bib" in meta:
        bib_entries = bib.parse_bib((post_dir / meta["bib"]).read_text())

    fig_count = 0

    def resolve_directive(kind, name, caption_html):
        nonlocal fig_count
        if kind == "figure":
            fig_count += 1
            fallback = (post_dir / f"{name}.svg").read_text()
            return (
                f"<figure class='breakout' id='fig-{name}' data-figure='{name}'>\n"
                f"<div class='fig-mount'>{fallback}</div>\n"
                f"<figcaption><span class='fig-label'>Figure {fig_count}.</span> {caption_html}</figcaption>\n"
                f"</figure>"
            )
        if kind == "table":
            content = (post_dir / f"{name}.html").read_text()
            return f"<figure class='breakout table-figure' id='tbl-{name}'>\n{content}\n</figure>"
        raise ValueError(f"unknown directive {kind}:{name}")

    parsed = dialect.parse(md, resolve_directive, bib_entries, katex.render_all)

    out_dir = OUT / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "markers.css").write_text(
        markers.generate_css(parsed["marker_colors"], meta.get("seed", 42))
    )

    scripts = []
    for f in sorted(post_dir.iterdir()):
        if f.suffix == ".js":
            shutil.copyfile(f, out_dir / f.name)
            scripts.append(f"<script src=\"{f.name}\" defer></script>")
        elif f.suffix == ".json" and f.name != "post.json":
            shutil.copyfile(f, out_dir / f.name)

    page = template
    for key, value in {
        "title": parsed["title"] or meta.get("title", slug),
        "description": meta.get("description", ""),
        "author": author,
        "date": meta.get("date", ""),
        "body": parsed["body"],
        "scripts": "\n".join(scripts),
    }.items():
        page = page.replace(f"$${key}$$", value)

    (out_dir / "index.html").write_text(page)
    print(f"built /blog/{slug}/ ({fig_count} figure(s), {len(parsed['marker_colors'])} marker(s), "
          f"{len(parsed['cite_keys'])} reference(s))")


def main():
    resume = check_resume_blog_entries()
    author = resume.get("name", "")
    template = (BLOG_SRC / "templates/post.html").read_text()

    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BLOG_SRC / "blog.css", OUT / "blog.css")

    for post_dir in sorted(CONTENT.iterdir()):
        if post_dir.is_dir() and (post_dir / "post.json").exists():
            build_post(post_dir, author, template)


if __name__ == "__main__":
    main()
