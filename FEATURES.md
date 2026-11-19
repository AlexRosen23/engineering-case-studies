# Engineering Case Studies: features

A public documentation repository with a small local reading site. It holds six sanitized case studies of private software projects: context, problem, constraints, approach, evidence, results with how they were measured, trade-offs, and what I'd do differently. Every figure is cited to the pull request, commit, file or test output it comes from; sources in private repositories are cited as dated plain text, never as links, hashes or paths. It is for engineers and reviewers who want to judge the work without access to the private source. The one thing it does best is show failures, limits and sources next to the results.

**This is the source-of-truth features list.** Every PR that adds, changes, removes or switches off something a person can see or use updates this file in the same PR (see "Keeping this file true").

- **Repo:** AlexRosen23/engineering-case-studies (public)
- **Status:** Published (documentation plus a static local site) · **Version:** none · **`main`:** `779c11a` (PR #6 merged)
- **Last updated:** 2026-11-16, written from the case studies, the checker, the site builder and the PR history.

**Status words** (a feature with no status word is live):
| Word | Means |
| --- | --- |
| *Live* | on `main` and readable on GitHub or through `./scripts/serve` |
| *In this PR* | added or changed by the open PR named in the change log, not merged yet (none right now) |
| *Planned* | named in the README as a next step, not done |

## At a glance
| | |
| --- | --- |
| Kind | Markdown case studies with Mermaid diagrams, plus a static reading site built from them (no server-side code, no JavaScript, no tracking) |
| Case studies | 6 files in `case-studies/` (106 to 180 lines each) |
| Sources | 102 numbered source notes: 97 private-repository citations as plain text and 5 from the private audit; the 150 PRs, commits and files behind them confirmed on GitHub on 2026-11-16 through a local-only map |
| Re-check | 85 claims from the original four re-checked: 70 held, 10 corrected, 5 updated (see `docs/method.md`) |
| Site | index, one page per study, method page; served on `127.0.0.1:6340` |
| Tests / CI | 25 unittest tests; GitHub Actions is disabled |
| Guards | gitleaks pre-commit and pre-push hooks; direct pushes to `main` refused |
| License | No license file, so default copyright applies |

## Contents
1. What it is and who it's for
2. How to run it
3. Architecture at a glance
4. Features
5. Integrations
6. Data and privacy
7. Tests and evidence
8. Known limits and gaps
9. Change log
10. Keeping this file true

## 1. What it is and who it's for
- **Purpose:** let someone judge private engineering work from a short, honest, cited write-up, since the source cannot be public.
- **Why the source is private:** personal data, licensed data, trading research that must not read as investment claims, a vendor protocol learned from interoperability analysis, and code with no license chosen yet.
- **Audience:** engineers and reviewers. Each case study ends with questions a reviewer can use to probe understanding, and the README offers a live walkthrough of the code.
- **How the work was built:** solo projects, with AI coding agents (mainly Claude Code) as implementers and Codex for read-only review. The owner sets requirements and safety rules, reviews and merges every change, and runs the systems.

## 2. How to run it
- **Read on GitHub:** the Markdown and Mermaid diagrams render there.
- **Reading site:** `./scripts/serve` builds `_site/` from the Markdown and serves it on loopback at port 6340 (`PORT` overrides). Python 3.9+, standard library only. Stop with Ctrl-C.
- **Checker:** `./scripts/run` (same as `python3 scripts/check.py`). `python3 scripts/check.py --online` also confirms every citation on GitHub (needs an authenticated `gh` with access to the private repos).
- **Tests:** `python3 -m unittest discover -s tests -v`.
- Optional, for contributors: `git config core.hooksPath .githooks` turns on the secret-scan hooks (needs `gitleaks`).

## 3. Architecture at a glance
```
README.md                 front page: tagline, use cases, index, run it, how it's made
case-studies/*.md         the six studies (13 sections, Mermaid, numbered sources, a meta line for the site)
docs/method.md            how claims are checked + the 2026-11-16 corrections table
data/repos.json           the public repositories a link may point to
scripts/serve             build + serve the site on loopback
scripts/build_site.py     Markdown -> HTML (footnotes, tables, lists, Mermaid -> SVG / message list)
scripts/site.css          the only stylesheet (system fonts, light/dark, phone layout)
scripts/run, check.py     the checker (structure, links, sanitization, citations, private exposure, site, --online)
tests/test_check.py       fixture-repo tests + real-repo tests + serve smoke test
.githooks/                gitleaks pre-commit and pre-push (+ main-branch guard)
```

## 4. Features

### The six case studies (`case-studies/`)
All share one outline: context, problem, constraints, my role, architecture (illustrative), approach, evidence, results and how they were measured, trade-offs and failures, what I'd do differently, why the source is private, questions, sources.
- **The Constellation** (`the-constellation.md`): agent observability with honest status, verified-by-use model routing, a benchmark-driven local model choice, and the integration and live-update pipeline that ships parallel agent PRs into the live app, with its RED runs and their causes.
- **PROVENANCE** (`provenance.md`): a signed, hash-chained claim → evidence → human-review trail with an offline verifier, test vectors, adversarial and tenant-isolation tests and a restore drill.
- **CHAOS MONKEY** (`chaos-monkey.md`): a retry/idempotency chaos lab where hypothesis E4 failed in 5 of 5 seeds, traced to the retry throttle, with E7's confounded pass and signed evidence (125 of 125 runs verified).
- **The Second Move** (`the-second-move.md`): an NFL tracking research pipeline with validated instruments, a locked holdout and a null result.
- **ELARA Command Deck** (`elara-command-deck.md`): approving AI-agent actions from a USB pad, and the firmware boot loops.
- **Scalp City** (`scalp-city.md`): tamper-evident append-only storage, a paper-only design enforced by tests, pre-registration, and a hardware fault caught by hashing. No strategy logic or results are published.

### Citations and re-checks
- **Numbered sources:** every claim's note names its source. Private repositories are cited as dated plain text ("Private repository (Scalp City): PR #14 (2026-10-26)") with no links, slugs, commit hashes or file paths (owner's decision, 2026-11-16); a few notes say "private evidence audit" and "not in git". Links are allowed only into public repositories listed in `data/repos.json`.
- **Results rule:** every line of a "Results" section that contains a number carries a citation.
- **Corrections in the open:** `docs/method.md` lists every claim that was corrected or updated on 2026-11-16, and each study marks its corrections.

### Reading site (`scripts/serve`, `scripts/build_site.py`)
- **Index** with one card per study (summary, topics, number of sources, evidence date) and a link to the method page.
- **Study pages** with an "On this page" table of contents, numbered source list with back-links, flowcharts drawn as SVG with a text version, and sequence diagrams as a numbered message list.
- **Navigation:** a "Case studies" nav on every page (the current page marked), so tools can plan screenshots from it.
- **Accessible and phone-ready:** skip link, landmarks, one h1 per page, focus outlines, scrollable tables, light and dark themes, a single-column layout under 820px.
- **No tracking:** no JavaScript, web fonts, cookies, analytics or third-party requests; `no-referrer`.

### Checker (`scripts/run`, `scripts/check.py`)
- **Structure:** 13 required sections, a Mermaid diagram and a meta line per study.
- **Links and sanitization:** relative links resolve; no emails, phone numbers, home paths or key-like strings.
- **Citations**: refs and definitions match; each source is a link into a listed public repo, a dated private-repository citation, or the private audit; uncited numbers in Results fail.
- **Private exposure**: fails on any URL, `owner/repo` or name-plus-PR-number reference to a non-public repo, any commit-hash-like token that is not a commit of this repo, and any file path that is not a file here, in the Markdown and in the built pages.
- **Site**: builds into a temp folder; each page has lang, title, one h1, main landmark, viewport and nav; internal links and anchors resolve; nothing loads from another host; no scripts; the visible text passes a privacy scan (localhost addresses, private IPs, home paths, env files, placeholders, trading figures).
- **`--online`** *(owner only)*: reads a local-only map (never committed: `~/.config/engineering-case-studies/private-citations.json` or a git-ignored `data/*.local.json`) from each footnote to its real PRs, commits and files, requires the PR numbers in the text to match it, and confirms every item exists on GitHub.

### Safety hooks (`.githooks/`)
- **Pre-commit secret scan** *(live once enabled)*: gitleaks on staged changes; blocks if gitleaks is missing or finds something.
- **Pre-push secret scan** *(live once enabled)*: scans commits the remote does not have yet.
- **Main-branch guard** *(live once enabled)*: refuses direct pushes to `main` unless `ALLOW_MAIN_PUSH=1` is set for one command.

## 5. Integrations
- No APIs or services at runtime. The site is static files served by Python's standard-library server on loopback.
- `--online` calls the GitHub API through `gh` (read-only), using the local-only citation map.
- The portfolio site's nightly scanner can use the documented start command `./scripts/serve` and port 6340.
- The hooks use the `gitleaks` command-line tool.

## 6. Data and privacy
- Stores only Markdown, one JSON registry, a stylesheet and scripts. No database, no user data, no telemetry.
- Contains no secrets, client names, credentials, trading logic, licensed row-level data or personal information, by the sanitization rule and the checker.
- Nothing points into the private repositories: citations show only the project's display name, a PR number or the kind of document, and a date. The map to real PRs, commits and files stays local.

## 7. Tests and evidence
- `tests/test_check.py`: 25 tests (fixture repos for each checker rule including the private-exposure rule and the online map match, the site builder output, sequence-diagram rendering, the real repo passing, and `scripts/serve` answering on a loopback port). All pass on this branch.
- `./scripts/run`: 0 problems on `main`. `python3 scripts/check.py --online` with the local map: 150 cited PRs, commits and files confirmed, 0 problems (2026-11-16).
- The site was checked by eye at 1600×1000 and phone width, light and dark.

## 8. Known limits and gaps
- **Private sources prove nothing to outsiders.** The live walkthrough is the mitigation.
- **Snapshots age:** each study gives its evidence date; numbers move as the projects change.
- **Some figures are secondhand:** a few come only from the 2026-11-08 private audit, and one validation in The Second Move was AI-scored. Both are labeled.
- **The Mermaid renderer is a subset:** flowcharts and sequence diagrams only; other diagram types fall back to the source text.
- **Planned:** publish The Second Move's aggregate Kaggle notebook before 2027-01-06.
- No license file; no CI.

## 9. Change log
| Date | PR | Change |
| --- | --- | --- |
| 2026-11-16 | #6 | Re-checked every claim against GitHub (10 corrected, 5 updated); rewrote the four studies to 13 sections with numbered sources; added PROVENANCE and CHAOS MONKEY; added the reading site (`scripts/serve`), citation and site checks, `--online`; private sources cited as plain text with a private-exposure rule (owner's decision); new tests; README tagline, use cases and Run it. |
| 2026-11-16 | #5 | Added `scripts/check.py`, `scripts/run`, `tests/` and a "Run it" README section. |
| 2026-11-16 | #4 | Added FEATURES.md. |
| 2026-11-11 | #3 | README: refresh verified ref, add PR #2 to history |
| 2026-11-10 | #2 | Link the merged README PR; map the hook files; hooks point to README |
| 2026-11-09 | #1 | Full README write-up (why the source is private, how case studies are made) |
| 2026-11-08 | none | Initial commit: four sanitized case studies, hooks, gitleaks config |

## Keeping this file true
- **Same PR, same change:** a PR that adds, edits or removes a case study, the site, the checker or a hook updates this file in that PR.
- **Status moves with reality:** change a status word when the thing changes; drop "in this PR" once merged.
- **Only what is true:** no secrets, no private-repo details beyond what the case studies already publish. Public repo: nothing goes in this file that is not already public here.
- **Repo gate:** `./scripts/run` and the tests pass; gitleaks hooks stay on; changes go through pull requests; Actions stay disabled unless the owner approves.
