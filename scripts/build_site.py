#!/usr/bin/env python3
"""Build the static reading site from the Markdown case studies.

usage: scripts/build_site.py [out-dir]        default out-dir: _site/ in the repo root (git-ignored)

Standard library only (Python 3.9+). The output is plain HTML and one stylesheet: no JavaScript, no web fonts, no
third-party requests and no analytics. The Markdown files stay the source of truth: GitHub renders them as they are,
and this script renders the same files for reading locally (scripts/serve).

Supported Markdown is the subset the case studies use: headings, paragraphs, **bold**, *italic*, `code`, links,
footnotes ([^id] with "[^id]: text" definitions), nested lists, pipe tables, blockquotes and fenced code. A
```mermaid block is drawn as an SVG (flowcharts) or a numbered list of messages (sequence diagrams), each with a
text version.
"""
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GH = re.compile(r"^https://github\.com/AlexRosen23/([A-Za-z0-9._-]+)(?:/(pull|commit|blob|tree|issues)/([^\s)#]+))?")
META = re.compile(r"<!--\s*meta:\s*(\{.*?\})\s*-->", re.S)
FOOTREF = re.compile(r"\[\^([A-Za-z0-9_-]+)\](?!:)")
FOOTDEF = re.compile(r"^\[\^([A-Za-z0-9_-]+)\]:\s*(.*)$")


def load_repos(root=ROOT):
    with open(os.path.join(root, "data", "repos.json"), encoding="utf-8") as fh:
        return json.load(fh)


def esc(s):
    return html.escape(s, quote=True)


def slug_id(text):
    s = re.sub(r"<[^>]+>", "", text).lower()
    s = re.sub(r"[^a-z0-9 -]", "", s).strip().replace(" ", "-")
    return re.sub(r"-+", "-", s) or "section"


# ---------------------------------------------------------------- inline Markdown


class Ctx:
    """Per-page state: footnote numbering, repo visibility, and which .md links map to which pages."""

    def __init__(self, repos, pages):
        self.repos = repos
        self.pages = pages  # {"the-constellation.md": "the-constellation.html"}
        self.order = []  # footnote ids in order of first reference
        self.refs = {}  # id -> count of references so far

    def footnote(self, fid):
        if fid not in self.order:
            self.order.append(fid)
        self.refs[fid] = self.refs.get(fid, 0) + 1
        n = self.order.index(fid) + 1
        rid = f"ref-{fid}" + ("" if self.refs[fid] == 1 else f"-{self.refs[fid]}")
        return f'<sup class="fn"><a href="#src-{esc(fid)}" id="{rid}" aria-label="Source {n}">[{n}]</a></sup>'


def link_html(text, href, ctx):
    m = GH.match(href)
    if m:
        vis = ctx.repos.get(m.group(1), "unknown")
        if vis == "private":
            return (f'<a class="gh private" href="{esc(href)}" rel="noreferrer">{text}</a>'
                    '<span class="badge" title="Private repository: the link opens for the owner and invited reviewers">private</span>')
        return f'<a class="gh" href="{esc(href)}" rel="noreferrer">{text}</a>'
    if re.match(r"^[a-z][a-z0-9+.-]*:", href):
        return f'<a href="{esc(href)}" rel="noreferrer">{text}</a>'
    base, _, frag = href.partition("#")
    target = ctx.pages.get(os.path.basename(base), base) if base else ""
    return f'<a href="{esc(target + ("#" + frag if frag else ""))}">{text}</a>'


def inline(text, ctx):
    """Render one line or paragraph of inline Markdown. Code spans are protected first so nothing inside them changes."""
    out, codes = [], []

    def keep_code(m):
        codes.append(f"<code>{esc(m.group(1))}</code>")
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep_code, text)
    text = esc(text).replace("&lt;br/&gt;", "<br>").replace("&lt;br&gt;", "<br>")
    text = FOOTREF.sub(lambda m: ctx.footnote(m.group(1)), text)
    # links: [text](href); the text was escaped above, the href is unescaped and re-escaped once in link_html
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: link_html(m.group(1), html.unescape(m.group(2)), ctx), text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    out.append(text)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], "".join(out))


# ---------------------------------------------------------------- diagrams

NODE = re.compile(r'^\s*([A-Za-z0-9_]+)\s*(\[\(|\(\(|\(\[|\[|\(|\{)?(.*?)(\)\]|\)\)|\]\)|\]|\)|\})?\s*$')


def parse_node(tok, labels):
    m = NODE.match(tok)
    if not m:
        return None
    nid, label = m.group(1), m.group(3)
    if m.group(2):
        label = label.strip().strip('"')
        labels[nid] = label
    else:
        labels.setdefault(nid, nid)
    return nid


def parse_flowchart(lines):
    labels, edges, direction = {}, [], "LR"
    m = re.match(r"^\s*(?:flowchart|graph)\s+(LR|RL|TD|TB|BT)", lines[0])
    if m:
        direction = "TD" if m.group(1) in ("TD", "TB", "BT") else "LR"
    order = []
    for raw in lines[1:]:
        line = raw.strip()
        if not line or line.startswith("%%") or re.match(r"^(subgraph|end$|classDef|class |style |direction )", line):
            continue
        parts = re.split(r"\s*(?:-->|-\.->|==>|---)(?:\|([^|]*)\|)?\s*", line)
        # re.split with a group interleaves labels: [node, label, node, label, node]
        groups = parts[0::2]
        elabels = parts[1::2]
        prev = None
        for i, g in enumerate(groups):
            ids = [parse_node(t, labels) for t in g.split("&")]
            ids = [x for x in ids if x]
            for x in ids:
                if x not in order:
                    order.append(x)
            if prev:
                for a in prev:
                    for b in ids:
                        edges.append((a, b, (elabels[i - 1] or "").strip()))
            prev = ids
    return direction, order, labels, edges


def layout(order, edges):
    layer = {n: 0 for n in order}
    for _ in range(len(order)):
        changed = False
        for a, b, _l in edges:
            if a != b and layer[b] < layer[a] + 1 and layer[a] + 1 < len(order):
                layer[b] = layer[a] + 1
                changed = True
        if not changed:
            break
    cols = {}
    for n in order:
        cols.setdefault(layer[n], []).append(n)
    return layer, cols


def flowchart_svg(src, title):
    direction, order, labels, edges = parse_flowchart(src.splitlines())
    if not order:
        return ""
    layer, cols = layout(order, edges)
    if len(cols) > 4:  # long chains read better top-down than as a strip too wide to read on a page
        direction = "TD"
    lines_of = {n: labels[n].split("<br/>") for n in order}
    char_w, line_h, pad, gap_main, gap_cross = 6.6, 16, 10, (46 if direction == "LR" else 26), 14
    box_w = {n: max(len(x) for x in lines_of[n]) * char_w + 2 * pad for n in order}
    box_h = {n: len(lines_of[n]) * line_h + 2 * pad - 4 for n in order}
    pos = {}
    if direction == "LR":
        x = 10
        for c in sorted(cols):
            w = max(box_w[n] for n in cols[c])
            y = 10
            for n in cols[c]:
                pos[n] = (x + (w - box_w[n]) / 2, y)
                y += box_h[n] + gap_cross
            x += w + gap_main
        width = x - gap_main + 10
        height = max(pos[n][1] + box_h[n] for n in order) + 10
    else:
        y = 10
        rows = []
        for c in sorted(cols):
            rows.append((c, y))
            y += max(box_h[n] for n in cols[c]) + gap_main
        width = max(sum(box_w[n] for n in cols[c]) + gap_cross * (len(cols[c]) - 1) for c in cols) + 20
        for c, ry in rows:
            total = sum(box_w[n] for n in cols[c]) + gap_cross * (len(cols[c]) - 1)
            x = (width - total) / 2
            for n in cols[c]:
                pos[n] = (x, ry)
                x += box_w[n] + gap_cross
        height = y - gap_main + 10
    tid = "d-" + slug_id(title)[:40]
    out = [f'<svg class="diagram" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-labelledby="{tid}" xmlns="http://www.w3.org/2000/svg">',
           f'<title id="{tid}">{esc(title)}</title>',
           '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
           '<path d="M0,0 L10,5 L0,10 z" class="arrowhead"/></marker></defs>']
    for a, b, _l in edges:
        (ax, ay), (bx, by) = pos[a], pos[b]
        if direction == "LR":
            x1, y1, x2, y2 = ax + box_w[a], ay + box_h[a] / 2, bx, by + box_h[b] / 2
            if layer[b] <= layer[a]:  # back or same-layer edge: route from the bottom
                x1, y1, x2, y2 = ax + box_w[a] / 2, ay + box_h[a], bx + box_w[b] / 2, by
        else:
            x1, y1, x2, y2 = ax + box_w[a] / 2, ay + box_h[a], bx + box_w[b] / 2, by
        out.append(f'<line class="edge" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" marker-end="url(#arrow)"/>')
    for n in order:
        x, y = pos[n]
        out.append(f'<rect class="node" x="{x:.1f}" y="{y:.1f}" width="{box_w[n]:.1f}" height="{box_h[n]:.1f}" rx="6"/>')
        for i, t in enumerate(lines_of[n]):
            ty = y + pad + 9 + i * line_h
            out.append(f'<text x="{x + box_w[n] / 2:.1f}" y="{ty:.1f}" text-anchor="middle">{esc(t)}</text>')
    out.append("</svg>")
    flat = lambda n: " ".join(labels[n].split("<br/>"))
    text = "".join(f"<li>{esc(flat(a))} → {esc(flat(b))}{(' (' + esc(l) + ')') if l else ''}</li>" for a, b, l in edges)
    return ("".join(out), f'<details class="alt"><summary>The diagram as text</summary><ul>{text}</ul></details>')


def sequence_html(src):
    names, rows = {}, []
    for raw in src.splitlines()[1:]:
        line = raw.strip()
        m = re.match(r"^participant\s+(\S+)\s+as\s+(.+)$", line)
        if m:
            names[m.group(1)] = m.group(2)
            continue
        m = re.match(r"^(alt|else|opt)\s*(.*)$", line)
        if m:
            rows.append(("note", f"{m.group(1)} {m.group(2)}".strip()))
            continue
        m = re.match(r"^(\S+?)\s*(-->>|->>|-->|->|--x|-x)\s*(\S+?)\s*:\s*(.+)$", line)
        if m:
            rows.append(("msg", (m.group(1), m.group(3), m.group(4), m.group(2).startswith("--"))))
    items, num = [], 0
    short = lambda k: re.sub(r"\s*\(.*\)$", "", names.get(k, k))
    for kind, v in rows:
        if kind == "note":
            items.append(f'<li class="branch">{esc("If " + v.split(" ", 1)[1] if v.startswith("alt") else v)}</li>')
        else:
            a, b, msg, reply = v
            num += 1
            items.append(f'<li value="{num}"><span class="who">{esc(short(a))}</span> <span aria-hidden="true">{"⇠" if reply else "→"}</span>'
                         f'<span class="sr"> to </span> <span class="who">{esc(short(b))}</span>: {esc(msg)}</li>')
    return f'<ol class="sequence">{"".join(items)}</ol>'


def diagram(src, title):
    first = src.strip().splitlines()[0] if src.strip() else ""
    if first.startswith("sequenceDiagram"):
        return f'<figure class="figure"><figcaption>{esc(title)} (sequence, in order)</figcaption>{sequence_html(src.strip())}</figure>'
    res = flowchart_svg(src.strip(), title)
    if not res:
        return f"<pre><code>{esc(src)}</code></pre>"
    svg, alt = res
    return f'<figure class="figure"><figcaption>{esc(title)}</figcaption><div class="svgwrap">{svg}</div>{alt}</figure>'


# ---------------------------------------------------------------- block Markdown


def render(md, ctx, page_title=""):
    """Markdown text -> (html body, toc entries [(id, text)], footnote definitions {id: text})."""
    md = META.sub("", md)
    lines = md.split("\n")
    out, toc, defs = [], [], {}
    i, n = 0, len(lines)
    used_ids = set()
    current_h2 = page_title

    def para(buf):
        if buf:
            out.append(f"<p>{inline(' '.join(x.strip() for x in buf), ctx)}</p>")

    buf = []
    while i < n:
        line = lines[i]
        if line.strip().startswith("```"):
            para(buf), buf.clear()
            lang = line.strip()[3:].strip()
            j = i + 1
            while j < n and not lines[j].strip().startswith("```"):
                j += 1
            body = "\n".join(lines[i + 1:j])
            out.append(diagram(body, f"Diagram: {current_h2}") if lang == "mermaid" else f"<pre><code>{esc(body)}</code></pre>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            para(buf), buf.clear()
            level, text = len(m.group(1)), m.group(2).strip()
            hid = slug_id(text)
            k = 2
            while hid in used_ids:
                hid = f"{slug_id(text)}-{k}"
                k += 1
            used_ids.add(hid)
            if level == 2:
                toc.append((hid, text))
                current_h2 = text
            out.append(f'<h{level} id="{hid}">{inline(text, ctx)}</h{level}>')
            i += 1
            continue
        fm = FOOTDEF.match(line)
        if fm:
            para(buf), buf.clear()
            text = fm.group(2)
            j = i + 1
            while j < n and lines[j].startswith("    ") and lines[j].strip():
                text += " " + lines[j].strip()
                j += 1
            defs[fm.group(1)] = text
            out.append(f"\x01DEF:{fm.group(1)}\x01")
            i = j
            continue
        if line.startswith(">"):
            para(buf), buf.clear()
            j = i
            q = []
            while j < n and lines[j].startswith(">"):
                q.append(lines[j][1:].strip())
                j += 1
            out.append(f'<blockquote><p>{inline(" ".join(q), ctx)}</p></blockquote>')
            i = j
            continue
        if line.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|\s*$", lines[i + 1]):
            para(buf), buf.clear()
            cells = lambda s: [c.strip() for c in s.strip().strip("|").split("|")]
            head = cells(line)
            j = i + 2
            rows = []
            while j < n and lines[j].startswith("|"):
                rows.append(cells(lines[j]))
                j += 1
            th = "".join(f'<th scope="col">{inline(c, ctx)}</th>' for c in head)
            tb = "".join("<tr>" + "".join(f"<td>{inline(c, ctx)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f'<div class="tablewrap" tabindex="0" role="region" aria-label="Table"><table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>')
            i = j
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", line):
            para(buf), buf.clear()
            j = i
            items = []
            while j < n and (re.match(r"^\s*([-*]|\d+\.)\s+", lines[j]) or (lines[j].startswith("  ") and lines[j].strip())):
                lm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[j])
                if lm:
                    items.append([len(lm.group(1)), lm.group(2)[0].isdigit(), lm.group(3)])
                else:
                    items[-1][2] += " " + lines[j].strip()
                j += 1
            out.append(list_html(items, ctx))
            i = j
            continue
        if not line.strip():
            para(buf), buf.clear()
            i += 1
            continue
        buf.append(line)
        i += 1
    para(buf)
    return "\n".join(out), toc, defs


def list_html(items, ctx):
    html_out, stack = [], []
    for indent, ordered, text in items:
        while stack and indent < stack[-1][0]:
            html_out.append("</li></%s>" % stack.pop()[1])
        if not stack or indent > stack[-1][0]:
            tag = "ol" if ordered else "ul"
            stack.append((indent, tag))
            html_out.append(f"<{tag}>")
        else:
            html_out.append("</li>")
        html_out.append(f"<li>{inline(text, ctx)}")
    while stack:
        html_out.append("</li></%s>" % stack.pop()[1])
    return "".join(html_out)


def sources_html(defs, ctx):
    """Replace the footnote-definition markers with one ordered source list, numbered in order of first reference."""
    unref = [d for d in defs if d not in ctx.order]
    items = []
    for fid in ctx.order + unref:
        text = defs.get(fid, "(missing source)")
        back = f' <a class="back" href="#ref-{esc(fid)}" aria-label="Back to the text">↩</a>' if fid in ctx.order else ""
        items.append(f'<li id="src-{esc(fid)}">{inline(text, ctx)}{back}</li>')
    return f'<ol class="sources">{"".join(items)}</ol>'


# ---------------------------------------------------------------- pages

CSS_FILE = "style.css"


def page(title, body, nav, description, current=""):
    cur = ' aria-current="page"'
    links = "".join(
        f'<li><a href="{esc(href)}"{cur if href == current else ""}>{esc(label)}</a></li>' for label, href in nav)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(description)}">
<meta name="referrer" content="no-referrer">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{CSS_FILE}">
</head>
<body>
<a class="skip" href="#main">Skip to the content</a>
<header class="site">
<div class="wrap"><a class="brand" href="./">Engineering case studies</a><span class="by">Alex T. Rosen</span></div>
</header>
<div class="wrap layout">
<nav class="studies" aria-label="Case studies"><h2 class="navhead">Case studies</h2><ul>{links}</ul></nav>
<main id="main">
{body}
</main>
</div>
<footer class="site"><div class="wrap"><p>Static pages built from the Markdown in this repository. No scripts, cookies or tracking.
<a href="method.html">How the claims are checked</a>.</p></div></footer>
</body>
</html>
"""


def load_studies(root=ROOT):
    d = os.path.join(root, "case-studies")
    studies = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        with open(os.path.join(d, f), encoding="utf-8") as fh:
            text = fh.read()
        m = META.search(text)
        try:
            meta = json.loads(m.group(1)) if m else {}
        except ValueError as e:
            raise SystemExit(f"{f}: the meta line is not valid JSON ({e})")
        h1 = re.search(r"^#\s+(.+)$", text, re.M)
        meta.setdefault("order", 99)
        meta.setdefault("nav", h1.group(1).split(":")[0].strip() if h1 else f[:-3])
        studies.append({"file": f, "text": text, "meta": meta, "title": h1.group(1).strip() if h1 else f[:-3],
                        "html": f[:-3] + ".html"})
    studies.sort(key=lambda s: (s["meta"]["order"], s["file"]))
    return studies


def build(out_dir, root=ROOT):
    repos = load_repos(root)
    studies = load_studies(root)
    pages = {s["file"]: s["html"] for s in studies}
    pages["method.md"] = "method.html"
    nav = [(s["meta"]["nav"], s["html"]) for s in studies]
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "site.css"), os.path.join(out_dir, CSS_FILE))
    written = []

    def write(name, text):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            fh.write(text)
        written.append(name)

    cards = []
    total_sources = 0
    for s in studies:
        ctx = Ctx(repos, pages)
        body, toc, defs = render(s["text"], ctx, s["title"])
        body = re.sub(r"(?:\x01DEF:[^\x01]+\x01\n?)+", lambda m: sources_html(defs, ctx), body, count=1)
        body = re.sub(r"\x01DEF:[^\x01]+\x01\n?", "", body)
        total_sources += len(defs)
        toc_html = "".join(f'<li><a href="#{hid}">{esc(re.sub(r"[*`]", "", t))}</a></li>' for hid, t in toc)
        h1_end = body.find("</h1>") + 5
        body = (body[:h1_end] + f'<nav class="toc" aria-label="On this page"><h2 class="navhead">On this page</h2><ol>{toc_html}</ol></nav>'
                + body[h1_end:])
        write(s["html"], page(f'{s["meta"]["nav"]} · Engineering case studies', f"<article>{body}</article>", nav,
                              s["meta"].get("summary", s["title"]), s["html"]))
        snap = esc(s["meta"].get("snapshot", ""))
        tags = "".join(f"<li>{esc(t)}</li>" for t in s["meta"].get("tags", []))
        cards.append(f'<li class="card"><h3><a href="{s["html"]}">{esc(s["title"])}</a></h3>'
                     f'<p>{esc(s["meta"].get("summary", ""))}</p><ul class="tags" aria-label="Topics">{tags}</ul>'
                     f'<p class="small">{len(defs)} cited sources · evidence as of {snap}</p></li>')
    intro = (
        "<h1>Engineering case studies</h1>"
        '<p class="lede">Write-ups of private software projects: the context, the constraints, what was built, how it was '
        "tested, what went wrong and what I would change. Every number is cited to the pull request, commit or report file "
        "it comes from, and anything that did not hold up on re-checking has been corrected.</p>"
        "<p>The code is mostly written by AI coding agents (Claude Code, with Codex for read-only review). Each study says "
        "which decisions were mine. The source repositories are private for the reasons each study gives, so their sources "
        "are cited as plain text (project, PR number, date) without links, and each one can be shown in a live walkthrough. "
        '<a href="method.html">How the claims are checked</a>.</p>'
        f'<h2 id="studies">{len(studies)} case studies</h2><ul class="cards">{"".join(cards)}</ul>'
    )
    write("index.html", page("Engineering case studies · Alex T. Rosen", intro, nav,
                             "Sanitized, cited engineering case studies of private projects.", ""))
    with open(os.path.join(root, "docs", "method.md"), encoding="utf-8") as fh:
        ctx = Ctx(repos, pages)
        body, _toc, defs = render(fh.read(), ctx, "Method")
        body = re.sub(r"(?:\x01DEF:[^\x01]+\x01\n?)+", lambda m: sources_html(defs, ctx), body, count=1)
        body = body.replace("{{STUDIES}}", str(len(studies))).replace("{{SOURCES}}", str(total_sources))
    write("method.html", page("How the claims are checked · Engineering case studies", f"<article>{body}</article>", nav,
                              "How every claim in the case studies is sourced, cited and checked.", "method.html"))
    return written


def main(argv):
    out = argv[0] if argv else os.path.join(ROOT, "_site")
    written = build(out)
    print(f"built {len(written)} pages into {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
