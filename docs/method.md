# How the claims are checked

These case studies describe private projects, so a reader cannot rerun them. The next best thing is to make every claim traceable and to show what changed when the claims were checked again. This page explains the rules and lists every correction.

## The rules

- **A number appears only with a source.** Each figure carries a numbered note naming the pull request, commit, file or test output it comes from.
- **No pointers into private repositories.** The sources live in private repositories, so this public repository cites them as dated plain text, such as "Private repository (Scalp City): PR #14 (2026-10-26)". It shows no links, repository slugs, commit hashes or file paths (owner's decision, 2026-11-16). The project's public display name is used instead.
- **A few figures come from a private audit, and say so.** On 2026-11-08 a read-only audit counted and re-ran parts of each project. Where a figure exists only in that audit (for example a test run on a copy, or row counts over licensed data that may not be committed), its note says "private evidence audit" and "not in git".
- **Lab numbers say they are lab numbers.** The hardware, the run count and who scored a rubric are given next to the result.
- **AI authorship is stated.** Each study says the code is agent-written and which decisions were mine.
- **Sanitized by rule.** No client names or data, credentials, trading logic or parameters, licensed row-level data or personal information. Diagrams are illustrative, with no hostnames, ports or paths.

## What the checker enforces

`./scripts/run` (the same as `python3 scripts/check.py`) fails if:

- a case study is missing a required section (context, problem, constraints, my role, architecture, approach, evidence, results, trade-offs, what I'd do differently, why the source is private, questions, sources) or its diagram;
- a citation has no source, a source is never cited, or a source is neither a link into a listed public repository, a dated private-repository citation, nor the private evidence audit;
- any page, link or text exposes a private repository: a URL or `owner/repo` reference to a repository not listed as public, a reference like "name" followed by "#12", a commit-hash-like token that is not a commit of this repository, or a file path that is not a file here;
- a line in a "Results" section contains a number but no citation;
- a page of this site has a broken link or anchor, loads anything from another host, contains a script, or shows a localhost address, a private IP address, a home-folder path or a placeholder;
- any page source contains an email address, phone number, home path or key-like string.

`python3 scripts/check.py --online` checks the private citations without publishing where they point. A local-only map, never committed, ties each footnote to its real pull requests, commits and files. The check requires the PR numbers shown in the public text to match the map exactly, then asks GitHub (through an authenticated `gh`) that every mapped item exists. On 2026-11-16 it confirmed all 150 cited PRs, commits and files. Only the owner has the map and access, so only the owner can run this step.

Today the site has {{STUDIES}} case studies with {{SOURCES}} numbered sources.

## Re-check of 2026-11-16

The four original case studies (measured 2026-11-08) were re-checked claim by claim against GitHub. 85 claims were checked: 70 held as written (some now carry an added qualifier), 10 were corrected and 5 were updated to a newer figure. Of the 70, 6 can be traced only to the private audit and are labeled that way, and 2 are statements about my role that git cannot show.

| Case study | Was | Now | Why |
|---|---|---|---|
| The Constellation | 21 safety-lab suites | 20 test files (the docs said 21) | file count at the snapshot commit |
| The Constellation | the outage fix added "a guard script and a pre-merge diff check" | the fix changed the ignore rule; the later guard is verify-pr's hygiene check | the named script is older and checks something else |
| The Constellation | 3,641 of 3,641 unit tests | the same, on a fix branch, not on `main` | the state doc says so |
| The Constellation | Piper vs `say`: 28 vs 903 ms | the same, for a 2-word line; 121 vs 938 ms for a sentence | the benchmark has three lengths |
| ELARA Command Deck | 194 Swift tests in 22 suites | 238 tests in 26 suites | 194 was the library target only |
| ELARA Command Deck | the code assumed a 4×3 grid | 3 rows of 4 keys | the code and docs said 3×4 |
| ELARA Command Deck | I recovered the device after 3 boot loops | recovery is recorded for the first two | the hardware log does not record the third |
| ELARA Command Deck | 205 gateway tests; "the newer main reports 230" | 230 on `main` | updated |
| ELARA Command Deck | named ELARA | the UI is now ORION; the repository keeps the name | updated |
| Scalp City | two database corruptions | three | the third incident report |
| Scalp City | a hardware memory fault | "faulty memory (or the storage path)", likely, not proven | no diagnostic result is recorded |
| Scalp City | 8–10 GB per session | about 6 GB after the storage change; busy days about 9.2 GB | updated |
| Scalp City | 499 test functions | 587 now (499 at the snapshot) | updated |
| The Second Move | precision 0.970, recall 0.967 vs the vendor | the same on Combine data; 0.951 and 0.881 on game tracking | the scope was missing |
| The Second Move | blind audit 0.977 | the same, and 0.886 recall under the first scoring order | both orders are reported in the repo |
| The Second Move | "pooled held-out MSE change of −0.29%", with nested CV among the rules | −0.29% relative reduction (negative is worse), pooled across both class directions; nested CV was secondary | wording and the primary analysis |
| The Second Move | 232 tests | 240 on 2026-11-11 | updated |

The two newer case studies, PROVENANCE and CHAOS MONKEY, were written on 2026-11-16 from their repositories, with every figure cited the same way.

## What this cannot do

A citation into a private repository proves nothing to someone who cannot open it, which is why these citations are plain text rather than links that would fail. The mitigation is the same as before: I'm happy to walk through any cited pull request, commit or file live.
