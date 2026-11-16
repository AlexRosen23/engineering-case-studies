"""Tests for scripts/check.py against throwaway fixture repos, plus the real repo."""
import importlib.util
import os
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("check", os.path.join(REPO, "scripts", "check.py"))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

GOOD = """# Title

## Problem and audience
x
## My role
x
## Architecture (illustrative)
```mermaid
flowchart LR
  a --> b
```
## Failures and tradeoffs
x
## Why the source is private
x
## Questions I'm happy to go deeper on
x
"""


def make_repo(study=GOOD, readme="# R\n[s](case-studies/a.md)\n"):
    d = tempfile.TemporaryDirectory()
    os.makedirs(os.path.join(d.name, "case-studies"))
    with open(os.path.join(d.name, "README.md"), "w") as f:
        f.write(readme)
    with open(os.path.join(d.name, "case-studies", "a.md"), "w") as f:
        f.write(study)
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
        p = self.problems(study=GOOD.replace("## My role\nx\n", ""))
        self.assertTrue(any("my role" in x for x in p), p)

    def test_missing_mermaid_is_reported(self):
        p = self.problems(study=GOOD.replace("```mermaid", "```text"))
        self.assertTrue(any("no mermaid" in x for x in p), p)

    def test_broken_relative_link_is_reported_but_urls_and_anchors_are_not(self):
        readme = "[gone](case-studies/missing.md) [web](https://example.org/x) [here](#top) [ok](case-studies/a.md#s)\n"
        p = self.problems(readme=readme)
        self.assertEqual(len(p), 1)
        self.assertIn("missing.md", p[0])

    def test_links_inside_code_fences_are_ignored(self):
        p = self.problems(readme="```\n[x](nowhere.md)\n```\n")
        self.assertEqual(p, [])

    def test_sanitization_scan_finds_each_kind(self):
        dirty = GOOD + "mail a.b@example.com, call 312-555-0142, path /Users/someone/x, key " + "AKIA" + "ABCDEFGHIJKLMNOP" + "\n"
        labels = " ".join(self.problems(study=dirty))
        for kind in ("email address", "phone number", "local path", "key-like string"):
            self.assertIn(kind, labels)


class RealRepo(unittest.TestCase):
    def test_the_published_case_studies_pass(self):
        docs, problems = check.run(REPO)
        self.assertGreaterEqual(len(docs), 5)
        self.assertEqual(problems, [])

    def test_run_wrapper_exit_code(self):
        r = subprocess.run([os.path.join(REPO, "scripts", "run")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 problem(s)", r.stdout)


if __name__ == "__main__":
    unittest.main()
