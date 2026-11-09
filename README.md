# Engineering case studies: Alex T. Rosen

I'm an Informatics graduate (Indiana University, 2025) and a cloud/data consultant. I build AI-agent systems, data pipelines and research tooling with explicit safety and evidence rules. These are sanitized write-ups of four private projects: what each one does, how it's built, how it was tested, what went wrong, and what I measured.

**How I build:** these are solo projects built with AI coding agents as implementers, mainly Claude Code, with Codex for read-only review. I set the requirements and safety rules, review and merge every change, and run the systems. The write-ups say which decisions were mine.

| Case study | What it shows |
|---|---|
| [The Constellation](case-studies/the-constellation.md) | Agent observability and provenance, multi-provider LLM routing, a local voice assistant with a benchmark-driven model choice, about 4,600 unit tests |
| [ELARA Command Deck](case-studies/elara-command-deck.md) | Human-in-the-loop approval of AI-agent actions from a physical USB pad, safety-first protocol design, hardware failure recovery |
| [Scalp City](case-studies/scalp-city.md) | Tamper-evident, append-only data storage, a paper-only design enforced by tests, pre-registered evaluation, a hardware-fault incident |
| [The Second Move](case-studies/the-second-move.md) | A research pipeline over 22.7M tracking frames, synthetic-truth validation, a locked holdout, and an honestly reported null result |

## Ground rules for these write-ups
- Every number was measured or counted from the project on 2026-11-08, or is labeled as coming from project docs. Lab benchmarks say they are lab benchmarks.
- No client data, credentials, trading logic, licensed competition data or personal information appears here. Diagrams are illustrative.
- The source repositories are private, and each case study says why. I'm happy to walk through any of them live.

Live public project: [LAST LEGEND](https://alexrosen23.github.io/LASTLEGEND/), a browser game with GitHub Actions regression tests.
