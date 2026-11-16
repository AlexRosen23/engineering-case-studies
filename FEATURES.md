# Engineering Case Studies: features

A public documentation repository. It holds four sanitized write-ups of private software projects: what each one does, how it is built, how it was tested, what went wrong and what was measured. It is for engineers and reviewers who want to judge the work without access to the private source. The one thing it does best is show failures, limits and sources next to the results.

**This is the source-of-truth features list.** Every PR that adds, changes, removes or switches off something a person can see or use updates this file in the same PR (see "Keeping this file true").

- **Repo:** AlexRosen23/engineering-case-studies (public) · **Folder:** `~/Desktop/Claude Projects/Engineering Case Studies`
- **Status:** Published (documentation only, no code) · **Version:** none · **`main`:** `b63fe99` (2026-11-15)
- **Last updated:** 2026-11-15, written from the README, the case-study files, the git hooks and the PR history.

**Status words** (a feature with no status word is live):
| Word | Means |
| --- | --- |
| *Live* | on `main` and readable on GitHub |
| *Planned* | named in the README as a next step, not done |

## At a glance
| | |
| --- | --- |
| Kind | Documentation repository. Markdown with Mermaid diagrams. No code to run. |
| Case studies | 4 files in `case-studies/` (55, 48, 65 and 58 lines) |
| Diagrams | 4 Mermaid blocks, one per case study (counted from source 2026-11-15) |
| README | 173 lines |
| Numbers inside the case studies | Snapshot measured on 2026-11-08 |
| Tests / CI | None. GitHub Actions is disabled. |
| Guards | gitleaks pre-commit and pre-push hooks; direct pushes to `main` refused |
| PRs merged | 3 (#1, #2, #3) |
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
- **Purpose:** let someone judge private engineering work from a short, honest write-up, since the source cannot be public.
- **Why the source is private** (from the README): personal data, licensed data, trading research that must not read as investment claims, and a vendor protocol learned from interoperability analysis.
- **Audience:** engineers and reviewers. Each case study ends with questions a reviewer can use to probe understanding, and the README offers a live walkthrough of the code.
- **How the work was built:** solo projects, with AI coding agents (mainly Claude Code) as implementers and Codex for read-only review. The owner sets requirements and safety rules, reviews and merges every change, and runs the systems.

## 2. How to run it
There is nothing to install or run. Read the files on GitHub, where the Mermaid diagrams render.

To read locally:
1. `git clone https://github.com/AlexRosen23/engineering-case-studies.git`
2. `cd engineering-case-studies`
3. `ls case-studies/` (four Markdown files)

Optional, for contributors: `git config core.hooksPath .githooks` turns on the secret-scan hooks (needs `gitleaks` installed). No environment variables, ports or dev servers.

## 3. Architecture at a glance
```
README.md                 front page: purpose, principles, index, how it was made
case-studies/             the four write-ups (Markdown + one Mermaid diagram each)
.githooks/pre-commit      gitleaks scan of staged changes
.githooks/pre-push        gitleaks scan of pushed commits + refuses direct pushes to main
.gitleaks.toml            secret-scan settings
.gitignore                baseline (no .env, keys, databases or dependencies)
```
Publishing flow (from the README): measure the projects, record every claim with source and date in a private evidence bank, draft, run a written sanitization checklist, run gitleaks plus a pattern scan, then publish.

## 4. Features

### The four case studies (`case-studies/`)
All four share one outline so they can be compared: problem and audience, role, architecture (illustrative), key choices, verification, failures and tradeoffs, why the source is private, and questions. Each has a "My role" section that states which decisions were the owner's and that the code is agent-written.
- **The Constellation** (`case-studies/the-constellation.md`): a local-first command center for AI coding agents. Covers agent observability and provenance, multi-provider LLM routing, a local voice assistant with a benchmark-driven model choice, and about 4,600 unit tests. Has an extra "Measured results" section, labeled as lab results.
- **ELARA Command Deck** (`case-studies/elara-command-deck.md`): approving AI-agent actions from a physical USB pad. Covers human-in-the-loop approval, safety-first protocol design and hardware failure recovery.
- **Scalp City** (`case-studies/scalp-city.md`): an auditable, paper-only market research platform. Covers tamper-evident append-only storage, a paper-only design enforced by tests, pre-registered evaluation and a hardware-fault incident. No strategy logic or results are published.
- **The Second Move** (`case-studies/the-second-move.md`): an NFL tracking-data research pipeline over 22.7M frames. Covers synthetic-truth validation, a locked holdout and an honestly reported null result. Its middle sections follow the research (data scale, validation, main test, engineering) instead of "key choices" and "verification".

### Honesty rules the write-ups follow (README "Principles")
- **Every number measured, dated and sourced** *(live)*: counted from the project on 2026-11-08 or labeled as taken from project docs. Lab benchmarks say they are lab benchmarks.
- **Failures get a section** *(live)*: each case study has "Failures and tradeoffs".
- **AI authorship stated** *(live)*: each case study says the code is agent-written and lists the owner's decisions.
- **Sanitized by rule** *(live)*: no client names or data, credentials, trading logic or parameters, licensed data or personal information. Diagrams carry no hostnames, ports or paths.
- **Questions to probe** *(live)*: each case study ends with questions a reviewer can ask.

### README (`README.md`)
- **Problem and approach comparison** *(live)*: why public repos, tech lists and demos fall short.
- **Case-study index table** *(live)*: one row per study with what it shows.
- **"What works today" table** *(live)*: item, status and how it was verified.
- **How it works diagram** *(live)*: Mermaid flow from private repos to this repo.
- **How it was built, limitations, repository map, testing and CI, related links** *(live)*. Related links point to three other public project repos and one public browser game.

### Safety hooks (`.githooks/`)
- **Pre-commit secret scan** *(live once enabled)*: runs gitleaks on staged changes with redacted output; blocks the commit if gitleaks is missing or finds something.
- **Pre-push secret scan** *(live once enabled)*: scans commits the remote does not have yet.
- **Main-branch guard** *(live once enabled)*: refuses direct pushes to `main`, including deleting it. The deliberate exception is `ALLOW_MAIN_PUSH=1` for one command. Changes go through pull requests.

## 5. Integrations
- No APIs, services or data sources.
- Links out to other public repos: Morrowglass Model Foundry, The Inkfall Vault, Spectral Canary Works, and the LAST LEGEND browser game.
- The hooks use the `gitleaks` command-line tool.

## 6. Data and privacy
- Stores only Markdown text. No database, no user data, no telemetry.
- Contains no secrets, client names, credentials, trading logic, licensed data or personal information, by the sanitization rule above.
- Source repositories for the four projects are private and not included.
- The Second Move's aggregate Kaggle notebook is *Planned* (see section 8).

## 7. Tests and evidence
- There is no code and no test suite. Counted from source on 2026-11-15, not run.
- Recorded checks (README, 2026-11-09): every relative link resolves to a file; each case study has the listed sections and one Mermaid block; a scan for emails, phone numbers, local paths and key-like strings found nothing.
- Recorded (README): gitleaks and a pattern scan before the first push on 2026-11-08; README verified on 2026-11-11 against `main`.
- Figures inside the case studies are a 2026-11-08 snapshot measured in the private repos and are not re-measured here.

## 8. Known limits and gaps
- **Snapshot that ages:** numbers describe 2026-11-08; one case study already notes a newer count.
- **Not independently reproducible** without the source. The live walkthrough offer is the mitigation.
- **Some figures are secondhand** (from project docs), and one validation in The Second Move was scored by an AI reviewer. Both are labeled where they appear.
- **Planned:** refresh the numbers when a project reaches a milestone; publish The Second Move's aggregate Kaggle notebook before the 2027-01-06 deadline.
- No license file; no CI.

## 9. Change log
| Date | PR | Change |
| --- | --- | --- |
| 2026-11-11 | #3 | README: refresh verified ref, add PR #2 to history |
| 2026-11-10 | #2 | Link the merged README PR; map the hook files; hooks point to README |
| 2026-11-09 | #1 | Full README write-up (why the source is private, how case studies are made) |
| 2026-11-08 | none | Initial commit: four sanitized case studies, hooks, gitleaks config |

## Keeping this file true
- **Same PR, same change:** a PR that adds, edits or removes a case study, the README structure or a hook updates this file in that PR.
- **Status moves with reality:** change a status word when the thing changes.
- **Only what is true:** no secrets, no private-repo details beyond what the case studies already publish. Public repo: nothing goes in this file that is not already public here.
- **Repo gate:** gitleaks hooks stay on; changes go through pull requests, and Actions stay disabled unless the owner approves.
