"""The blog's markdown dialect -> HTML.

Processing order is load-bearing:
  1. Math ($$...$$ display, $...$ inline) is stashed into opaque \\x00 tokens FIRST,
     so no later regex ever sees TeX. Tokens are substituted with KaTeX HTML at the
     very end, and the body is infilled into the page template after that — which is
     also why $$...$$ math can coexist with the template's $$key$$ placeholders.
  2. Pastel markers  ***{cN}(text)***  /  **{cN}(text)**  (same syntax as the resume).
  3. Bold **text** (negative lookahead keeps it off marker syntax).
  4. Citations [@key] / [@a; @b], numbered by first appearance; %%references%% block.
  5. Links [text](url)  (target=_blank only for external urls).
Blocks: '# ' title, '## ' section, blank-line paragraphs, and %%directive%% lines.
"""
import re

from bib import format_entry, hover_text
from markers import COLORS

MATH_TOKEN = "\x00M{}\x00"
REFS_TOKEN = "\x00REFS\x00"


def parse(md, resolve_directive, bib_entries, render_math):
    """Returns dict(title, body, marker_colors, cite_keys).

    resolve_directive(kind, name, caption_html) -> html for %%figure:...%% / %%table:...%%
    render_math(list[(tex, display)]) -> list[html]
    """
    math = []

    def stash(tex, display):
        math.append((tex.strip(), display))
        return MATH_TOKEN.format(len(math) - 1)

    md = re.sub(r"\$\$(.+?)\$\$", lambda m: stash(m.group(1), True), md, flags=re.S)
    md = re.sub(r"\$(.+?)\$", lambda m: stash(m.group(1), False), md)

    marker_colors = []
    cite_keys = []

    def plain(text, context):
        if re.search(r"[<\x00\[]", text):
            raise ValueError(f"marker text must be plain (no links/math/html): {context!r}")
        return text

    def cite(m):
        links = []
        for key in (k.strip().lstrip("@") for k in m.group(1).split(";")):
            if key not in bib_entries:
                raise KeyError(f"citation key not in bibliography: {key}")
            if key not in cite_keys:
                cite_keys.append(key)
            n = cite_keys.index(key) + 1
            links.append(
                f"<a class='cite' href='#ref-{key}' title=\"{hover_text(bib_entries[key])}\">{n}</a>"
            )
        return f"<span class='cite-group'>[{', '.join(links)}]</span>"

    def link(m):
        target = " target='_blank'" if m.group(2).startswith("http") else ""
        return f"<a href='{m.group(2)}'{target}>{m.group(1)}</a>"

    def inline(text):
        def highlight(m):
            marker_colors.append(COLORS[m.group(1)])
            return f"<mark class='marker{len(marker_colors) - 1}'>{plain(m.group(2), m.group(0))}</mark>"

        def underline(m):
            marker_colors.append(COLORS[m.group(1)])
            return f"<mark class='marker{len(marker_colors) - 1} underline'>{plain(m.group(2), m.group(0))}</mark>"

        text = re.sub(r"\*\*\*\{(c[1-5])\}\((.*?)\)\*\*\*", highlight, text)
        text = re.sub(r"\*\*\{(c[1-5])\}\((.*?)\)\*\*", underline, text)
        text = re.sub(r"\*\*(?!\{)(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\[(@[^\]]+)\]", cite, text)
        text = re.sub(r"\[([^\]@][^\]]*)\]\(([^)]+)\)", link, text)
        return text

    title = None
    blocks = []
    para = []

    def flush():
        if not para:
            return
        text = " ".join(l.strip() for l in para).strip()
        para.clear()
        if not text:
            return
        if re.fullmatch(r"\x00M\d+\x00", text):
            blocks.append(text)  # display equation stands alone, no <p>
        else:
            blocks.append(f"<p>{inline(text)}</p>")

    for line in md.split("\n"):
        s = line.strip()
        if not s:
            flush()
        elif s.startswith("# ") and title is None:
            flush()
            title = s[2:].strip()
        elif s.startswith("## "):
            flush()
            blocks.append(f"<h2>{inline(s[3:].strip())}</h2>")
        elif s == "%%references%%":
            flush()
            blocks.append(REFS_TOKEN)
        elif m := re.fullmatch(r"%%(figure|table):([\w-]+)%%\s*(.*)", s):
            flush()
            blocks.append(resolve_directive(m.group(1), m.group(2), inline(m.group(3))))
        else:
            para.append(line)
    flush()

    body = "\n".join(blocks)

    refs = "\n".join(
        f"<li id='ref-{k}'>{format_entry(bib_entries[k])}</li>" for k in cite_keys
    )
    body = body.replace(
        REFS_TOKEN, f"<h2>References</h2>\n<ol class='references'>\n{refs}\n</ol>" if refs else ""
    )

    for i, html in enumerate(render_math(math)):
        body = body.replace(MATH_TOKEN.format(i), html)

    return {"title": title, "body": body, "marker_colors": marker_colors, "cite_keys": cite_keys}
