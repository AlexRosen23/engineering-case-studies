# The Second Move: NFL tracking research that reported a null result

> Sanitized case study. The repo must stay private under competition rules, and the data is licensed (CC BY-NC 4.0). Aggregates only; no player names. Built with AI agents: I prompted and edited the research brief with ChatGPT, Claude Code implemented, and Codex reviewed read-only. I set direction and scope, chose the exploratory write-up and approved merges. Research status: **exploratory; the confirmatory test was not run; nothing submitted yet** (deadline 2027-01-06).

## Problem and audience
Does player-tracking data reveal athletic traits, such as change-of-direction ability and tracked sprint speed, that predict on-field outcomes beyond the official NFL Combine numbers? The audience is the NFL Big Data Bowl and anyone who cares about sports-analytics rigor.

## My role
- Set direction and scope decisions: Kaggle data only, aggregate-only public output, the FastAPI plus React local tool.
- Set the review exit rules.
- When the results came back null, chose to publish them honestly as exploratory.

## Architecture (illustrative)
```mermaid
flowchart LR
  CSV[Competition CSVs] --> SC[Typed schema checks]
  SC --> PQ[Streaming CSV→Parquet<br/>DuckDB]
  PQ --> K[10 Hz Savitzky–Golay kinematics]
  K --> D[Redirection detector]
  D --> G[Cohort guard<br/>2025 class locked]
  G --> A[Player-grouped nested CV analyses]
  A --> O[Aggregate outputs + hash-stamped manifests]
  O --> APP[Local scouting app<br/>FastAPI + React, loopback only]
```

## Data scale (counts)
22,654,290 game-tracking frames; 463,189 Combine tracking rows (6,310 attempts); 314,197 player-play rows; 1,002 games; 510 players.

## Validation before analysis
| Check | Result |
|---|---|
| Detector on 3,591 synthetic cuts with known truth | 99.75% detected, 0% extra events, 4.67° angle RMSE, 0.046 s timing RMSE |
| Detector vs vendor kinematics (Combine) | precision 0.970, recall 0.967 (recorded in project docs) |
| Blind audit, 49 real sequences | precision and recall 0.977. **Scored by an AI reviewer**, so not human validation. |
| Forty-yard peak speed reliability | ICC(1) 0.84–0.98 within position. Redirection-trait repeatability not established. |

## The main test, and its null result
- **Question:** does tracked forty-yard peak speed improve prediction of receiver separation beyond official Combine data, position, route and coverage?
- **Rules fixed before fitting:** a 5% minimum effect, player-grouped nested CV, train-only preprocessing, and the 2025 class locked.
- **Result:** pooled held-out MSE change of **−0.29% (interval −0.70 to +0.11)**. Not meaningful. Promotion to a confirmatory test was **stopped**.
- Three other candidate programs were stopped or killed at their gates.

## Engineering
- 232 pytest tests pass (run 2026-11-08).
- 14 saved review rounds. The final blocking-only review found 5 issues, all fixed before merge: a cross-origin write risk, a cohort-boundary bypass through stored citations, a mislabeled "pre-snap" field, a UI overclaim and bytecode writes.

## Failures and tradeoffs
- No pre-registration file was written, so the claim is "threshold fixed before fitting", not "pre-registered".
- The AI-scored audit is interim and labeled as such.
- The honest headline is weaker than a positive finding. That was the right trade.

## Why the source is private
Competition rules require a private repository and limit how the licensed data can be shared. A public Kaggle notebook with aggregate results is planned before the 2027-01-06 deadline.

## Questions I'm happy to go deeper on
1. Why group CV folds by player, and what leaks if you don't?
2. Your power simulation gave about 80.6%. What would make you trust a null?
3. What's the difference between "threshold fixed before fitting" and pre-registration?
