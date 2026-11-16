"""Tests for scripts/check.py and scripts/build_site.py against throwaway fixture repos, plus the real repo."""
import importlib.util
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
spec = importlib.util.spec_from_file_location("check", os.path.join(REPO, "scripts", "check.py"))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
import build_site  # noqa: E402

def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


PR = "https://github.com/AlexRosen23/demo/pull/7"  # demo is listed as PUBLIC in the fixture registry
PRIVATE_NOTE = "Private repository (Demo): PR #7 (2026-11-16)."
GOOD = """<!-- meta: {"nav": "Demo", "order": 1, "snapshot": "2026-11-16", "summary": "A demo.", "tags": ["x"]} -->
# Demo: a title

## Context
x
## Problem
x
## Constraints
x
## My role
x
## Architecture (illustrative)
```mermaid
flowchart LR
  a[Start] --> b[(Store)]
  b --> c[End<br/>two lines]
```
## Approach
x [^one]
## Evidence
x
## Results and how they were measured
| Result | Value |
|---|---|
| tests | 12 passed[^one] |

Measured 3 times[^one].
## Trade-offs and failures
x
## What I'd do differently
x
## Why the source is private
x
## Questions I'm happy to go deeper on
1. why?
## Sources
[^one]: """ + PRIVATE_NOTE + """
"""


def make_repo(study=GOOD, readme="# R\n[s](case-studies/a.md)\n", method="# Method\n\nText.\n"):
    d = tempfile.TemporaryDirectory()
    for sub in ("case-studies", "data", "docs"):
        os.makedirs(os.path.join(d.name, sub))
    files = {"README.md": readme, "case-studies/a.md": study, "docs/method.md": method,
             "data/repos.json": '{"demo": "public"}'}
    for rel, text in files.items():
        with open(os.path.join(d.name, rel), "w") as f:
            f.write(text)
    return d


class Checker(unittest.TestCase):
    def problems(self, **kw):
        d = make_repo(**kw)
        try:
            return check.run(d.name)[1]
        finally:
            d.cleanup()

    def test_clean_repo_has_no_problems(self):
        self.assertEqual(self.problems(), [])

    def test_missing_section_is_reported(self):
        p = self.problems(study=GOOD.replace("## Constraints\nx\n", ""))
        self.assertTrue(any("constraints" in x for x in p), p)

    def test_missing_mermaid_is_reported(self):
        p = self.problems(study=GOOD.replace("```mermaid", "```text"))
        self.assertTrue(any("no mermaid" in x for x in p), p)

    def test_missing_meta_is_reported(self):
        p = self.problems(study=re.sub(r"<!-- meta:.*?-->\n", "", GOOD))
        self.assertTrue(any("meta" in x for x in p), p)

    def test_broken_relative_link_is_reported_but_urls_and_anchors_are_not(self):
        readme = "[gone](case-studies/missing.md) [web](https://example.org/x) [here](#top) [ok](case-studies/a.md#s)\n"
        p = self.problems(readme=readme)
        self.assertEqual(len(p), 1, p)
        self.assertIn("missing.md", p[0])

    def test_links_inside_code_fences_are_ignored(self):
        p = self.problems(readme="```\n[x](nowhere.md)\n```\n")
        self.assertEqual(p, [])

    def test_sanitization_scan_finds_each_kind(self):
        dirty = GOOD + "mail a.b@example.com, call 312-555-0142, path /Users/someone/x, key " + "AKIA" + "ABCDEFGHIJKLMNOP" + "\n"
        labels = " ".join(self.problems(study=dirty))
        for kind in ("email address", "phone number", "local path", "key-like string"):
            self.assertIn(kind, labels)

    # citations
    def test_undefined_and_unused_citations_are_reported(self):
        p = self.problems(study=GOOD.replace("x [^one]", "x [^two]"))
        joined = " ".join(p)
        self.assertIn("[^two] has no source", joined)

    def test_source_must_cite_something_checkable(self):
        p = self.problems(study=GOOD.replace(PRIVATE_NOTE, "a blog post"))
        self.assertTrue(any("cites no pull request" in x for x in p), p)
        for ok_note in ("Private evidence audit, 2026-11-08. Not in git", "[demo#7](" + PR + ")"):
            self.assertEqual(self.problems(study=GOOD.replace(PRIVATE_NOTE, ok_note)), [], ok_note)

    def test_private_citation_needs_a_date(self):
        p = self.problems(study=GOOD.replace(PRIVATE_NOTE, "Private repository (Demo): PR #7."))
        self.assertTrue(any("has no date" in x for x in p), p)

    def test_unpinned_file_link_into_a_public_repo_is_reported(self):
        unpinned = GOOD.replace(PRIVATE_NOTE, "[r](https://github.com/AlexRosen23/demo/blob/main/README.md)")
        self.assertTrue(any("not pinned" in x for x in self.problems(study=unpinned)))

    # private exposure
    def test_link_into_a_non_public_repo_fails(self):
        p = self.problems(study=GOOD.replace(PRIVATE_NOTE, "[x](https://github.com/AlexRosen23/secret-repo/pull/3) (2026-11-16)"))
        joined = " ".join(p)
        self.assertIn("not a listed public repository", joined)
        self.assertIn("non-public repository URL", joined)

    def test_private_slug_hash_and_path_in_text_fail(self):
        for leak, label in (("see secret-repo#12 for details", "non-public repository's pull request"),
                            ("fixed in commit 2d88ae8 that day", "commit-hash-like token"),
                            ("read src/secret/thing.py for it", "not a file of this repository"),
                            ("owned by AlexRosen23/secret-repo", "names a non-public repository")):
            p = self.problems(study=GOOD.replace("## Problem\nx", "## Problem\n" + leak))
            self.assertTrue(any(label in x for x in p), (leak, p))

    def test_own_files_and_library_names_are_not_leaks(self):
        p = self.problems(study=GOOD.replace("## Problem\nx", "## Problem\nsee docs/method.md, README.md and three.js"))
        self.assertEqual(p, [])

    def test_online_map_must_match_the_pr_numbers_in_the_text(self):
        texts = {"case-studies/a.md": GOOD}
        entry = [{"repo": "hidden", "kind": "pull", "ref": "7"}, {"repo": "hidden", "kind": "commit", "ref": "abc1234"}]
        probs, todo = check.check_private_map(texts, {"case-studies/a.md": {"one": entry}})
        self.assertEqual(probs, [])
        self.assertEqual(len(todo), 2)
        wrong = [{"repo": "hidden", "kind": "pull", "ref": "8"}]
        probs, _ = check.check_private_map(texts, {"case-studies/a.md": {"one": wrong}})
        self.assertTrue(any("shows PRs ['7'] but the map has ['8']" in x for x in probs), probs)
        probs, _ = check.check_private_map(texts, {})
        self.assertTrue(any("no entry" in x for x in probs), probs)

    def test_uncited_number_in_results_is_reported(self):
        p = self.problems(study=GOOD.replace("Measured 3 times[^one].", "Measured 3 times."))
        self.assertTrue(any("uncited number in Results" in x for x in p), p)

    # site
    def test_site_pages_have_landmarks_and_no_external_resources(self):
        d = make_repo()
        try:
            with tempfile.TemporaryDirectory() as out:
                written = build_site.build(out, d.name)
                self.assertEqual(sorted(written), ["a.html", "index.html", "method.html"])
                page = read(os.path.join(out, "a.html"))
                self.assertIn('<html lang="en">', page)
                self.assertIn('aria-label="Case studies"', page)
                self.assertNotIn("<script", page)
                self.assertNotIn("github.com/AlexRosen23", page)  # private sources are plain text
                self.assertIn('id="src-one"', page)  # the source list is rendered and linked
                self.assertIn("<svg", page)  # the flowchart became an SVG
                self.assertIn("The diagram as text", page)
        finally:
            d.cleanup()

    def test_site_privacy_scan_and_broken_site_link(self):
        p = self.problems(method="# Method\n\nServed at 127.0.0.1:6340 and [gone](nowhere.md).\n")
        joined = " ".join(p)
        self.assertIn("localhost URL", joined)
        self.assertIn("broken link", joined)

    def test_sequence_diagram_renders_as_ordered_messages(self):
        html_out = build_site.diagram("sequenceDiagram\n  participant A as Agent\n  A->>B: ask\n  alt risky\n  B-->>A: no\n  end", "t")
        self.assertIn("<ol class=\"sequence\">", html_out)
        self.assertIn("Agent", html_out)
        self.assertIn("If risky", html_out)


class RealRepo(unittest.TestCase):
    def test_the_published_case_studies_pass(self):
        docs, problems = check.run(REPO)
        self.assertGreaterEqual(len(docs), 7)
        self.assertEqual(problems, [])

    def test_no_committed_file_points_into_a_private_repo(self):
        repos = build_site.load_repos(REPO)
        self.assertTrue(all(v == "public" for v in repos.values()), repos)  # the registry names no private repo
        for rel in ["README.md", "FEATURES.md", "docs/method.md"] + ["case-studies/" + f for f in os.listdir(os.path.join(REPO, "case-studies"))]:
            for repo in re.findall(r"github\.com/AlexRosen23/([\w.-]+)", read(os.path.join(REPO, rel))):
                self.assertIn(repo, repos, rel)

    def test_run_wrapper_exit_code(self):
        r = subprocess.run([os.path.join(REPO, "scripts", "run")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 problem(s)", r.stdout)

    def test_every_case_study_page_links_at_least_two_others_for_navigation(self):
        with tempfile.TemporaryDirectory() as out:
            build_site.build(out, REPO)
            index = read(os.path.join(out, "index.html"))
            nav = re.search(r'<nav class="studies".*?</nav>', index, re.S).group(0)
            self.assertGreaterEqual(len(re.findall(r'href="[a-z0-9-]+\.html"', nav)), 2)

    def test_serve_script_serves_the_index_on_loopback(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        env = dict(os.environ, PORT=str(port))
        with tempfile.TemporaryDirectory():
            proc = subprocess.Popen([os.path.join(REPO, "scripts", "serve")], env=env, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            try:
                body = ""
                for _ in range(50):
                    try:
                        body = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1).read().decode()
                        break
                    except OSError:
                        time.sleep(0.2)
                self.assertIn("Engineering case studies", body)
            finally:
                proc.terminate()
                proc.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
