#!/usr/bin/env python3
"""Check the case studies and the reading site built from them.

usage: scripts/check.py [--online] [repo-root]

Exits 0 when clean, 1 when problems are found. Standard library only; reads files and builds the site into a
temporary folder, writes nothing in the repository. Checks:
  1. structure: every case study has the required sections, a Mermaid diagram and a meta line (summary, nav label, order);
  2. links: relative links in the Markdown resolve to files;
  3. sanitization: no email addresses, phone numbers, home-folder paths or key-like strings in any page source;
  4. citations: every [^ref] has a definition and every definition is used; each definition either links a pull
     request, commit or commit-pinned file in a PUBLIC repository listed in data/repos.json, or cites a private
     repository as dated plain text ("Private repository (Project): PR #12 (2026-11-03)"), or names the private
     evidence audit; every line of a "Results" section that contains a number carries a citation;
  4b. private exposure: no link or text may point into a private repository: no github.com/AlexRosen23 URL or
     "owner/repo" / "repo#12" reference to a repository that is not listed as public, no commit-hash-like token that
     is not a commit of this repository, and no file path that does not exist in this repository;
  5. site: the built pages each have a language, a title, one h1, a main landmark and the case-study navigation;
     every internal link and #fragment resolves; nothing loads from another host (no scripts, styles, images or
     frames from outside); the visible text passes a privacy scan;
  6. --online (optional, owner only, needs an authenticated `gh`): every public link resolves on GitHub, and every
     private citation is checked through a LOCAL map that is never committed (data/private-citations.local.json, or
     ~/.config/engineering-case-studies/private-citations.json, or $CASE_STUDY_CITATIONS). The map ties each
     footnote to its real pull requests, commits and files; the check requires the PR numbers in the public text to
     match the map exactly, then asks GitHub that each mapped item exists.
"""
import html
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_site  # noqa: E402

REQUIRED = [
    "context",
    "problem",
    "constraints",
    "my role",
    "architecture",
    "approach",
    "evidence",
    "results",
    "trade-offs",
    "what i'd do differently",
    "why the source is private",
    "questions",
    "sources",
]
META_KEYS = ("summary", "nav", "order", "snapshot", "tags")
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)\)")
SANITIZE = {
    "email address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}"),
    "phone number": re.compile(r"(?<!\d)(\+?1[ .-])?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"),
    "local path": re.compile(r"(/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+|[A-Z]:\\Users\\)"),
    "key-like string": re.compile(r"\b(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}|xox[bap]-[A-Za-z0-9-]{10,})\b"),
}
# what a published page must never show (mirrors the portfolio's screenshot privacy rules)
SITE_PRIVACY = {
    "localhost URL": re.compile(r"\b(?:localhost|127\.0\.0\.1):\d{2,5}"),
    "private IP address": re.compile(r"\b(?:10|127|192\.168|172\.(?:1[6-9]|2\d|3[01]))(?:\.\d{1,3}){2,3}\b"),
    "home path": re.compile(r"/Users/[\w.-]+|~/[A-Za-z.]"),
    "env file": re.compile(r"(?<![\w$)\]])\.env(?:\.[A-Za-z]+)?\b"),
    "placeholder": re.compile(r"\b(?:TODO|TBD|FIXME)\b|\b[Ll]orem [Ii]psum\b"),
    "trading figure": re.compile(r"\b(?:P&L|PnL|win rate)\s*[:=]?\s*[-+$]?\d", re.I),
    "machine hostname": re.compile(r"\.local\b|\.ts\.net\b", re.I),
}
GH_CITE = re.compile(r"https://github\.com/AlexRosen23/([A-Za-z0-9._-]+)/(pull|commit|blob)/([^\s)]+)")
GH_ANY = re.compile(r"github\.com/AlexRosen23/([A-Za-z0-9._-]+)", re.I)
OWNER_REPO = re.compile(r"\bAlexRosen23/([A-Za-z0-9._-]+)")
SLUG_PR = re.compile(r"(?<![\w/.-])([A-Za-z][\w.-]*[A-Za-z0-9])#\d+\b")
HEXISH = re.compile(r"(?<![\w/-])(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}(?![\w-])")
PATHISH = re.compile(r"(?<![\w./:-])((?:[\w.-]+/)*[\w-][\w.-]*\.(?:py|ts|tsx|js|mjs|cjs|swift|json|sql|toml|ya?ml|md|sh|go|rs))(?![\w/])")
NOT_PATHS = {"three.js", "node.js", "next.js", "vue.js", "d3.js", "react.js"}  # library names, not files
AUDIT_CITE = re.compile(r"private evidence audit", re.I)
PRIVATE_CITE = re.compile(r"private repositor(y|ies)", re.I)
DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
MAP_PATHS = ("data/private-citations.local.json", os.path.expanduser("~/.config/engineering-case-studies/private-citations.json"))
FOOTREF = re.compile(r"\[\^([A-Za-z0-9_-]+)\](?!:)")
FOOTDEF = re.compile(r"^\[\^([A-Za-z0-9_-]+)\]:\s*(.*)$", re.M)


def strip_code(text):
    """Drop fenced code blocks so links and patterns inside examples are not judged as prose."""
    return re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)


def headings(text):
    return [re.sub(r"^#+\s*", "", ln).strip().lower() for ln in strip_code(text).splitlines() if ln.startswith("#")]


def sections(text):
    """{lower-case h2 heading: [lines]} for the prose outside code fences."""
    out, cur = {}, None
    for ln in strip_code(text).splitlines():
        m = re.match(r"^##\s+(.*)$", ln)
        if m:
            cur = m.group(1).strip().lower()
            out[cur] = []
        elif cur is not None:
            out[cur].append(ln)
    return out


def check_case_study(path, text):
    problems = []
    found = headings(text)
    for want in REQUIRED:
        if not any(h.startswith(want) for h in found):
            problems.append(f"{path}: missing section '{want}'")
    if len(re.findall(r"^```mermaid\s*$", text, flags=re.M)) < 1:
        problems.append(f"{path}: no mermaid diagram")
    m = build_site.META.search(text)
    if not m:
        problems.append(f"{path}: no <!-- meta: {{...}} --> line")
    else:
        try:
            meta = json.loads(m.group(1))
            for k in META_KEYS:
                if k not in meta:
                    problems.append(f"{path}: meta has no '{k}'")
            if len(str(meta.get("nav", ""))) > 32:
                problems.append(f"{path}: meta nav label is longer than 32 characters")
        except ValueError as e:
            problems.append(f"{path}: meta is not valid JSON ({e})")
    return problems


def check_links(path, text, root):
    problems = []
    base = os.path.dirname(os.path.join(root, path))
    for target in LINK.findall(strip_code(text)):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue  # external URL, mailto or same-page anchor
        rel = target.split("#")[0]
        if rel and not os.path.exists(os.path.normpath(os.path.join(base, rel))):
            problems.append(f"{path}: broken link -> {target}")
    return problems


def check_sanitization(path, text):
    problems = []
    for label, rx in SANITIZE.items():
        for m in rx.finditer(text):
            problems.append(f"{path}: possible {label}: {m.group(0)[:40]}")
    return problems


def citations(text):
    """[(repo, kind, ref)] for every GitHub citation in the footnote definitions of a document."""
    out = []
    for _fid, body in FOOTDEF.findall(text):
        for repo, kind, ref in GH_CITE.findall(body):
            out.append((repo, kind, ref.rstrip(".,;")))
    return out


def check_citations(path, text, repos):
    problems = []
    prose = strip_code(text)
    refs = set(FOOTREF.findall(re.sub(r"^\[\^[A-Za-z0-9_-]+\]:.*$", "", prose, flags=re.M)))
    defs = dict(FOOTDEF.findall(prose))
    for r in sorted(refs - set(defs)):
        problems.append(f"{path}: citation [^{r}] has no source definition")
    for d in sorted(set(defs) - refs):
        problems.append(f"{path}: source [^{d}] is never cited")
    for fid, body in defs.items():
        cites = GH_CITE.findall(body)
        if not cites and not AUDIT_CITE.search(body) and not PRIVATE_CITE.search(body):
            problems.append(f"{path}: source [^{fid}] cites no pull request, commit, pinned file, private-repository source or the private evidence audit")
        if PRIVATE_CITE.search(body) and not DATE.search(body):
            problems.append(f"{path}: private-repository source [^{fid}] has no date")
        for repo, kind, ref in cites:
            if repos.get(repo) != "public":
                problems.append(f"{path}: source [^{fid}] links {repo}, which is not a listed public repository")
            if kind == "pull" and not re.match(r"^\d+(#.*)?$", ref):
                problems.append(f"{path}: source [^{fid}] has a malformed pull-request link ({ref})")
            if kind == "commit" and not re.match(r"^[0-9a-f]{7,40}$", ref):
                problems.append(f"{path}: source [^{fid}] has a malformed commit link ({ref})")
            if kind == "blob" and not re.match(r"^[0-9a-f]{7,40}/[^\s]+$", ref):
                problems.append(f"{path}: source [^{fid}] links a file that is not pinned to a commit ({ref})")
    # every Results line with a number carries a citation
    for name, lines in sections(text).items():
        if not name.startswith("results"):
            continue
        for ln in lines:
            s = ln.strip()
            if not s or re.match(r"^\|[\s:|-]+\|$", s) or s.startswith("[^"):
                continue
            if re.search(r"\d", re.sub(r"\[\^[^\]]+\]", "", s)) and not FOOTREF.search(s):
                if s.startswith("|") and s == next((x.strip() for x in lines if x.strip().startswith("|")), None):
                    continue  # a table's header row
                problems.append(f"{path}: uncited number in Results: {s[:70]}")
    return problems


def known_files(root):
    """Every file path in this repository (relative), plus the basenames, so a mention of our own files is allowed."""
    out = set()
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in (".git", "_site", "node_modules", "__pycache__")]
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")
            out.add(rel)
            out.add(f)
    return out


def own_commit(root, token):
    r = subprocess.run(["git", "-C", root, "cat-file", "-e", token + "^{commit}"], capture_output=True)
    return r.returncode == 0


def check_private_exposure(path, text, root, repos, files=None):
    """No link or text may point into a repository that is not public: URLs, owner/repo and repo#N references,
    commit-hash-like tokens that are not commits of this repository, and file paths that are not files here."""
    problems = []
    public = {k.lower() for k, v in repos.items() if v == "public"}
    files = files if files is not None else known_files(root)
    for repo in GH_ANY.findall(text):
        if repo.lower() not in public:
            problems.append(f"{path}: exposes a non-public repository URL (AlexRosen23/{repo})")
    for repo in OWNER_REPO.findall(text):
        if repo.lower() not in public and not repo.lower().startswith("alexrosen23"):
            problems.append(f"{path}: names a non-public repository (AlexRosen23/{repo})")
    scrub = re.sub(r"https?://\S+", " ", text)  # public links were judged above; their paths are fine
    scrub = re.sub(r"\]\([^)\s]*\)", "] ", scrub)  # relative link targets: check_links reports missing ones
    for slug in SLUG_PR.findall(scrub):
        if slug.lower() not in public:
            problems.append(f"{path}: '{slug}#N' points at a non-public repository's pull request")
    for tok in HEXISH.findall(scrub):
        if not own_commit(root, tok):
            problems.append(f"{path}: commit-hash-like token {tok} is not a commit of this repository")
    for m in PATHISH.finditer(scrub):
        p = m.group(1).lstrip("./")
        if p.lower() in NOT_PATHS or p in files or os.path.basename(p) in files or os.path.exists(os.path.normpath(os.path.join(root, os.path.dirname(path), m.group(1)))):
            continue
        problems.append(f"{path}: file path {m.group(1)} is not a file of this repository (a private path?)")
    return problems


class PageParser:
    """Tiny HTML scan: ids, links, resource URLs, landmarks and visible text (regex-based; the pages are generated)."""

    def __init__(self, text):
        self.text = text
        self.ids = set(re.findall(r'\sid="([^"]+)"', text))
        self.hrefs = re.findall(r'<a\s[^>]*href="([^"]*)"', text)
        self.resources = re.findall(r'<(?:script|link|img|iframe|source|video|audio|embed|object)\b[^>]*?(?:src|href|data)="([^"]*)"', text)
        body = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", text, flags=re.S)
        body = re.sub(r"<head>.*?</head>", " ", body, flags=re.S)
        self.visible = html.unescape(re.sub(r"<[^>]+>", " ", body))


def check_site(root):
    problems = []
    repos = build_site.load_repos(root)
    with tempfile.TemporaryDirectory() as out:
        try:
            written = build_site.build(out, root)
        except Exception as e:  # a build failure is a problem to report, not a crash
            return [f"site: build failed: {type(e).__name__}: {e}"], 0
        parsed = {}
        files = known_files(root)
        for name in written:
            with open(os.path.join(out, name), encoding="utf-8") as fh:
                parsed[name] = PageParser(fh.read())
        for name, p in parsed.items():
            t = p.text
            if not re.search(r'<html lang="[a-z]{2}', t):
                problems.append(f"site/{name}: no lang attribute")
            if not re.search(r"<title>[^<]+</title>", t):
                problems.append(f"site/{name}: no title")
            if len(re.findall(r"<h1[\s>]", t)) != 1:
                problems.append(f"site/{name}: needs exactly one h1")
            if '<main id="main"' not in t or 'aria-label="Case studies"' not in t:
                problems.append(f"site/{name}: missing main landmark or case-study navigation")
            if 'name="viewport"' not in t:
                problems.append(f"site/{name}: no viewport meta (phone layout)")
            for res in p.resources:
                if re.match(r"^(https?:)?//", res):
                    problems.append(f"site/{name}: loads a resource from another host: {res}")
            if re.search(r"<script\b", t):
                problems.append(f"site/{name}: contains a script")
            for href in p.hrefs:
                if re.match(r"^[a-z][a-z0-9+.-]*:", href):
                    if not href.startswith("https://"):
                        problems.append(f"site/{name}: non-https external link: {href}")
                    continue
                base, _, frag = href.partition("#")
                target = name if base in ("", ".") else ("index.html" if base in ("./", "/") else base)
                if target not in parsed:
                    problems.append(f"site/{name}: broken link -> {href}")
                elif frag and frag not in parsed[target].ids:
                    problems.append(f"site/{name}: missing anchor -> {href}")
            for label, rx in SITE_PRIVACY.items():
                m = rx.search(p.visible)
                if m:
                    problems.append(f"site/{name}: visible {label}: {m.group(0)[:40]}")
            for repo in re.findall(r'href="https://github\.com/AlexRosen23/([A-Za-z0-9._-]+)', t):
                if repos.get(repo) != "public":
                    problems.append(f"site/{name}: links a repository that is not public: {repo}")
            for prob in check_private_exposure(f"site/{name}", p.visible, root, repos, files):
                problems.append(prob)
        return problems, len(written)


def gh_exists(repo, kind, ref):
    if kind == "pull":
        api = f"repos/AlexRosen23/{repo}/pulls/{ref.split('#')[0]}"
    elif kind == "commit":
        api = f"repos/AlexRosen23/{repo}/commits/{ref}"
    else:
        sha, _, path = ref.partition("/")
        api = f"repos/AlexRosen23/{repo}/contents/{path.split('#')[0]}?ref={sha}"
    r = subprocess.run(["gh", "api", api, "--silent"], capture_output=True, text=True)
    return r.returncode == 0


def load_private_map(root):
    """The local-only citation map (never committed), or (None, None) when this machine has none."""
    for cand in ([os.environ["CASE_STUDY_CITATIONS"]] if os.environ.get("CASE_STUDY_CITATIONS") else []) + [
            os.path.join(root, MAP_PATHS[0]), MAP_PATHS[1]]:
        if os.path.exists(cand):
            try:
                with open(cand, encoding="utf-8") as fh:
                    return json.load(fh), cand
            except ValueError as e:
                raise SystemExit(f"online: the local private-citation map is not valid JSON ({e})")
    return None, None


def check_private_map(texts, mapping):
    """Offline half of the online check: every private-repository footnote has a map entry, and the PR numbers in the
    public text are exactly the mapped pull requests. Returns (problems, [(repo, kind, ref)] to ask GitHub about)."""
    problems, todo = [], []
    for rel, text in texts.items():
        fmap = mapping.get(rel, {})
        defs = dict(FOOTDEF.findall(strip_code(text)))
        for fid, body in defs.items():
            entry = fmap.get(fid)
            if PRIVATE_CITE.search(body) and not entry:
                problems.append(f"online: {rel} [^{fid}] cites a private repository but the local map has no entry for it")
                continue
            if not entry:
                continue
            shown = set(re.findall(r"#(\d+)", body))
            mapped = {str(c["ref"]).split("#")[0] for c in entry if c["kind"] == "pull"}
            if shown != mapped:
                problems.append(f"online: {rel} [^{fid}] shows PRs {sorted(shown)} but the map has {sorted(mapped)}")
            todo += [(c["repo"], c["kind"], c["ref"]) for c in entry]
        for fid in set(fmap) - set(defs):
            problems.append(f"online: the local map has {rel} [^{fid}], which no longer exists")
    return problems, todo


def check_online(all_cites, texts, root):
    problems = []
    mapping, where = load_private_map(root)
    todo = list(all_cites)
    if mapping is None:
        if any(PRIVATE_CITE.search(t) for t in texts.values()):
            problems.append("online: no local private-citation map on this machine, so private citations cannot be checked (owner only)")
    else:
        p, extra = check_private_map(texts, mapping)
        problems += p
        todo += extra
    for repo, kind, ref in sorted(set(todo)):
        if not gh_exists(repo, kind, ref):
            problems.append(f"online: a cited {kind} was not found on GitHub ({len(ref)}-character reference)")
    check_online.checked = len(set(todo))
    return problems


def run(root, online=False):
    problems = []
    repos = build_site.load_repos(root)
    studies = sorted(f for f in os.listdir(os.path.join(root, "case-studies")) if f.endswith(".md"))
    if not studies:
        problems.append("case-studies/: no case studies found")
    docs = ["README.md", "FEATURES.md", "docs/method.md"] + [f"case-studies/{f}" for f in studies]
    docs = [d for d in docs if os.path.exists(os.path.join(root, d))]
    all_cites, texts = [], {}
    files = known_files(root)
    for rel in docs:
        with open(os.path.join(root, rel), encoding="utf-8") as fh:
            text = fh.read()
        if rel.startswith("case-studies/"):
            problems += check_case_study(rel, text)
        if rel.startswith("case-studies/") or rel == "docs/method.md":
            problems += check_citations(rel, text, repos)
            all_cites += citations(text)
            texts[rel] = text
        problems += check_private_exposure(rel, text, root, repos, files)
        problems += check_links(rel, text, root)
        problems += check_sanitization(rel, text)
    site_problems, pages = check_site(root)
    problems += site_problems
    if online:
        problems += check_online(all_cites, texts, root)
    private = sum(len(re.findall(r"^\[\^[^\]]+\]:.*private repositor", t, flags=re.M | re.I)) for t in texts.values())
    run.stats = {"files": len(docs), "pages": pages, "citations": len(all_cites), "distinct": len(set(all_cites)),
                 "private": private, "online": getattr(check_online, "checked", 0) if online else 0}
    return docs, problems


def main(argv):
    online = "--online" in argv
    args = [a for a in argv if a != "--online"]
    root = args[0] if args else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs, problems = run(root, online=online)
    for p in problems:
        print("PROBLEM", p)
    s = run.stats
    online_note = f"; online: {s['online']} cited PRs, commits and files confirmed on GitHub" if online and not problems else ""
    print(f"checked {len(docs)} files, {s['pages']} site pages, {s['private']} private-repository sources (plain text, no links), "
          f"{s['citations']} public GitHub links{online_note}: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
