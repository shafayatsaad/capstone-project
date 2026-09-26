# AI usage log

## Assistance used

Codex helped turn the capstone brief into the initial design, API, provider interface, mismatch guard, generated demo corpus, dashboard, and documentation. It also suggested the deterministic offline fixture provider so evaluators can reproduce the acceptance flow without paid accounts or local model downloads.

## What needed judgment and correction

- The supplied PDF title and requirements did not match the existing repository's earlier lead-capture README/history. The implementation follows the PDF's image-matching capstone. The existing history was preserved and is disclosed in the README; a separate public repository is still required by the brief.
- Fixture tags can demonstrate validation and the refusal workflow, but they cannot establish real visual understanding. The dashboard, README, and cost log label the demo provider honestly. Actual model inference is available through Gemini API or optional local Ollama; a live Gemini run still requires my own private key in `.env`.
- A deterministic hashed embedding with a small synonym map is not a general semantic model. It is bounded to repeatable capstone probes; for broader language behavior, use Gemini or the local embedding provider and measure its quality on the labeled set.

## Ownership reflection

I reviewed each route, table, and guard rule against the capstone probes. I can explain the processing flow: image classification is validated by `ImageTags`, embeddings share a vector space, candidates are ranked, and `guard()` independently refuses low-confidence or mismatched candidates before they are offered. SQLite stores the run state and each provider operation's cost and attribution. I reran the labeled evaluation and verified the upload endpoint; `EVIDENCE.md` records those outputs. Before submission, I still need to run a live Gemini batch with my own key and publish to the dedicated public repository required by the brief.
