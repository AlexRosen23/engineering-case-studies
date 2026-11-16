#!/usr/bin/env python3
"""Check the case studies: required sections, a Mermaid block, relative links that resolve, and a sanitization scan.

usage: scripts/check.py [repo-root]     exits 0 when clean, 1 when problems are found.
Standard library only; reads files, writes nothing.
"""
import os
import re
import sys

REQUIRED = [
    "problem and audience",
    "my role",
    "architecture",
    "failures and tradeoffs",
    "why the source is private",
    "questions",
]
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)\)")
SANITIZE = {
    "email address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}"),
    "phone number": re.compile(r"(?<!\d)(\+?1[ .-])?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"),
    "local path": re.compile(r"(/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+|[A-Z]:\\Users\\)"),
    "key-like string": re.compile(r"\b(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}|xox[bap]-[A-Za-z0-9-]{10,})\b"),
}


def strip_code(text):
    """Drop fenced code blocks so links and patterns inside examples are not judged as prose."""
    return re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)


def headings(text):
    return [re.sub(r"^#+\s*", "", ln).strip().lower() for ln in strip_code(text).splitlines() if ln.startswith("#")]


def check_case_study(path, text):
    problems = []
    found = headings(text)
    for want in REQUIRED:
        if not any(h.startswith(want) for h in found):
            problems.append(f"{path}: missing section '{want}'")
    if len(re.findall(r"^```mermaid\s*$", text, flags=re.M)) < 1:
        problems.append(f"{path}: no mermaid diagram")
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


def run(root):
    problems = []
    studies = sorted(f for f in os.listdir(os.path.join(root, "case-studies")) if f.endswith(".md"))
    if not studies:
        problems.append("case-studies/: no case studies found")
    docs = ["README.md"] + [f"case-studies/{f}" for f in studies]
    for rel in docs:
        with open(os.path.join(root, rel), encoding="utf-8") as fh:
            text = fh.read()
        if rel.startswith("case-studies/"):
            problems += check_case_study(rel, text)
        problems += check_links(rel, text, root)
        problems += check_sanitization(rel, text)
    return docs, problems


def main(argv):
    root = argv[0] if argv else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs, problems = run(root)
    for p in problems:
        print("PROBLEM", p)
    print(f"checked {len(docs)} files: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
