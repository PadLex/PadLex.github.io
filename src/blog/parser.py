"""The blog's markdown dialect -> HTML.

Processing order is load-bearing:
  1. Math ($$...$$ display, $...$ inline) is stashed into opaque \\x00 tokens FIRST,
     so no later regex ever sees TeX. Tokens are substituted with KaTeX HTML at the
     very end, and the body is infilled into the page template after that — which is
     also why $$...$$ math can coexist with the template's $$key$$ placeholders.
  2. Pastel markers  ***{cN}(text)***  /  **{cN}(text)**  (same syntax as the resume).
  3. Bold **text** (negative lookahead keeps it off marker syntax), then *italic*.
  4. Citations, numbered by first appearance; %%references%% block. Two forms:
     [@key] / [@a; @b] -> [1, 2], and bare @key -> "Keskar et al. [1]" (textual,
     \\citet-style; @key's keeps the possessive on the author label).
  5. Links [text](url)  (target=_blank only for external urls).
Blocks: '# ' title, '## ' section, blank-line paragraphs, and %%directive%% lines.

%%startfold%% ... %%endfold%% wraps the blocks between the two markers in a collapsible
paper fold (see fold.js / fold.css). The markers stand alone — they are not tied to a
heading, so a fold can start a paragraph or two into a section.

%%startfold%% may also sit *inside* a paragraph, mid-sentence. The paragraph then goes
into the fold whole, and the lines above the marker's own line are left lying flat as a
lead-in, so the reader gets a few real lines before the paper bends away. Which line
that is depends on how the text wraps, so it is measured in the browser (fold.js) and
re-measured whenever the text reflows; all this file does is drop a marker span there.
"""
import re

from bib import citet_label, format_entry, hover_text
from markers import COLORS

FOLD_MARKER = "%%startfold%%"
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

    def cite_link(key):
        if key not in bib_entries:
            raise KeyError(f"citation key not in bibliography: {key}")
        if key not in cite_keys:
            cite_keys.append(key)
        n = cite_keys.index(key) + 1
        return f"<a class='cite' href='#ref-{key}' title=\"{hover_text(bib_entries[key])}\">{n}</a>"

    def cite(m):
        links = [cite_link(k.strip().lstrip("@")) for k in m.group(1).split(";")]
        return f"<span class='cite-group'>[{', '.join(links)}]</span>"

    def citet(m):
        key = m.group(1)
        link = cite_link(key)
        label = citet_label(bib_entries[key]) + (m.group(2) or "")
        return f"{label} <span class='cite-group'>[{link}]</span>"

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
        text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
        text = re.sub(r"\[(@[^\]]+)\]", cite, text)
        text = re.sub(r"@([A-Za-z][\w-]*)('s)?", citet, text)
        text = re.sub(r"\[([^\]@][^\]]*)\]\(([^)]+)\)", link, text)
        return text

    title = None
    blocks = []
    para = []
    fold = False  # inside %%startfold%% ... %%endfold%%
    fold_count = 0

    def open_fold():
        nonlocal fold, fold_count
        if fold:
            raise ValueError("%%startfold%% inside a fold; close the first one with %%endfold%%")
        fold = True
        fold_count += 1
        blocks.append(
            "<section class='fold'>\n"
            f"<div class='fold-body' id='fold-{fold_count}'>"
            "<div class='fold-panel fold-panel-lead'><div class='fold-content'>"
        )

    def close_fold():
        nonlocal fold
        if not fold:
            raise ValueError("%%endfold%% without a matching %%startfold%%")
        fold = False
        blocks.append(
            "</div></div>"  # content, lead panel
            "<span class='fold-crease fold-crease-top'></span>"
            "<span class='fold-crease fold-crease-mid'></span>"
            "<span class='fold-crease fold-crease-bottom'></span>"
            "</div>"  # body
            f"<button class='fold-toggle' type='button' aria-expanded='false' "
            f"aria-controls='fold-{fold_count}' aria-label='Unfold section'>"
            "<span class='fold-hint' aria-hidden='true'></span></button>"
            "</section>"
        )

    def require_flat(what):
        if fold:
            raise ValueError(f"{what} while a fold is open; close it with %%endfold%%")

    def flush():
        if not para:
            return
        text = " ".join(l.strip() for l in para).strip()
        para.clear()
        if not text:
            return
        if re.fullmatch(r"\x00M\d+\x00", text):
            blocks.append(text)  # display equation stands alone, no <p>
            return
        # A %%startfold%% mid-paragraph opens the fold before this paragraph and leaves a
        # marker where it stood; fold.js turns that into the line the paper bends on.
        found = text.count(FOLD_MARKER)
        if found > 1:
            raise ValueError(f"{found} %%startfold%% markers in one paragraph; use one")
        if found:
            open_fold()
        html = inline(text).replace(FOLD_MARKER, "<span class='fold-lift'></span>")
        blocks.append(f"<p>{html}</p>")

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
        elif s == FOLD_MARKER:
            flush()
            open_fold()
        elif s == "%%endfold%%":
            flush()
            close_fold()
        elif s == "%%references%%":
            flush()
            require_flat("%%references%%")
            blocks.append(REFS_TOKEN)
        elif m := re.fullmatch(r"%%(figure|table):([\w-]+)%%\s*(.*)", s):
            flush()
            blocks.append(resolve_directive(m.group(1), m.group(2), inline(m.group(3))))
        else:
            para.append(line)
    flush()
    require_flat("end of the post")

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
