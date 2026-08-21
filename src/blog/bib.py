"""Minimal BibTeX parsing and reference formatting. Handles only what the posts cite."""
import re

# common LaTeX accent commands -> unicode, applied before braces are stripped
ACCENTS = {
    '\\"a': "ä", '\\"o': "ö", '\\"u': "ü", '\\"A': "Ä", '\\"O': "Ö", '\\"U': "Ü",
    "\\'a": "á", "\\'e": "é", "\\'i": "í", "\\'o": "ó", "\\'u": "ú",
    "\\`a": "à", "\\`e": "è", "\\^o": "ô", "\\~n": "ñ", "\\c{c}": "ç",
    "\\ss": "ß", "\\&": "&", "--": "–",
}


def _delatex(value):
    for tex, ch in ACCENTS.items():
        value = value.replace(tex, ch)
    return value


def parse_bib(text):
    """Returns {key: {field: value}} for every @entry in the file."""
    entries = {}
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        depth, i = 1, m.end()
        start = i
        while depth and i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[start : i - 1]
        fields = {}
        for fm in re.finditer(r'(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|"[^"]*"|[^,\n]+)', body):
            val = fm.group(2).strip().rstrip(",").strip()
            if val and val[0] in '{"':
                val = val[1:-1]
            val = re.sub(r"[{}]", "", _delatex(val))
            fields[fm.group(1).lower()] = re.sub(r"\s+", " ", val).strip()
        entries[m.group(2)] = fields
    return entries


def _authors(fields):
    raw = fields.get("author", "")
    names = [a.strip() for a in raw.split(" and ") if a.strip()]
    # "Last, First" -> "First Last"
    names = [" ".join(reversed([p.strip() for p in n.split(",")])) if "," in n else n for n in names]
    return ", ".join(names)


def format_entry(fields):
    """One-line reference: Authors. Title. Venue, Year."""
    venue = fields.get("journal") or fields.get("booktitle") or fields.get("publisher") or ""
    tail = ", ".join(p for p in (venue, fields.get("year", "")) if p)
    parts = [p for p in (_authors(fields), fields.get("title", ""), tail) if p]
    return ". ".join(parts) + "."


def citet_label(fields):
    """In-text author label for bare @key citations: 'Keskar et al.',
    'Hochreiter and Schmidhuber', or a lone 'Jordan'."""
    names = [a.strip() for a in fields.get("author", "").split(" and ") if a.strip()]
    lasts = [n.split(",")[0].strip() if "," in n else n.split()[-1] for n in names]
    if len(lasts) == 1:
        return lasts[0]
    if len(lasts) == 2:
        return f"{lasts[0]} and {lasts[1]}"
    return f"{lasts[0]} et al."


def hover_text(fields):
    """Short text for the cite link's title attribute."""
    first = _authors(fields).split(",")[0].strip()
    year = fields.get("year", "")
    label = f"{first} et al." if "," in _authors(fields) else first
    return f"{label} ({year}): {fields.get('title', '')}" if year else f"{label}: {fields.get('title', '')}"
