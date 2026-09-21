"""Blog build: content/blogposts/<slug>/{post.json,post.md,...} -> docs/blog/<slug>/.

Runs AFTER (and independently of) the resume build. Never touches docs/index.html
or docs/markers.css.
"""
import json
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
SITE_URL = "https://padula.dev"

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
    if scripts:  # shared figure helpers load before any post figure script
        scripts.insert(0, "<script src=\"../fig.js\" defer></script>")

    note = meta.get("note", "")  # raw HTML: a credit between the title and byline
    if note:
        note = f'        <div class="post-note">{note}</div>'

    page = template
    for key, value in {
        "title": parsed["title"] or meta.get("title", slug),
        "description": meta.get("description", ""),
        "canonical_url": f"{SITE_URL}/blog/{slug}/",
        "author": author,
        "date": meta.get("date", ""),
        "note": note,
        "body": parsed["body"],
        "scripts": "\n".join(scripts),
    }.items():
        page = page.replace(f"$${key}$$", value)

    (out_dir / "index.html").write_text(page)
    print(f"built /blog/{slug}/ ({fig_count} figure(s), {len(parsed['marker_colors'])} marker(s), "
          f"{len(parsed['cite_keys'])} reference(s))")


def main():
    resume = json.loads((ROOT / "content/resume.json").read_text())
    # Posts are signed the way papers are, with the middle initial the resume
    # masthead leaves off.
    author = resume.get("author") or resume.get("name", "")
    template = (BLOG_SRC / "templates/post.html").read_text()

    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BLOG_SRC / "blog.css", OUT / "blog.css")
    shutil.copyfile(BLOG_SRC / "fig.js", OUT / "fig.js")
    shutil.copyfile(BLOG_SRC / "fold.js", OUT / "fold.js")
    shutil.copyfile(BLOG_SRC / "fold.css", OUT / "fold.css")
    static_dir = BLOG_SRC / "static"
    if static_dir.exists():
        shutil.copytree(static_dir, OUT / "static", dirs_exist_ok=True)

    post_urls = []
    for post_dir in sorted(CONTENT.iterdir()):
        if post_dir.is_dir() and (post_dir / "post.json").exists():
            build_post(post_dir, author, template)
            meta = json.loads((post_dir / "post.json").read_text())
            post_urls.append(f"{SITE_URL}/blog/{meta['slug']}/")

    urls = [f"{SITE_URL}/", *post_urls]
    sitemap_entries = "\n".join(f"  <url><loc>{url}</loc></url>" for url in urls)
    (ROOT / "docs/sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{sitemap_entries}\n"
        "</urlset>\n"
    )
    (ROOT / "docs/robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )


if __name__ == "__main__":
    main()
