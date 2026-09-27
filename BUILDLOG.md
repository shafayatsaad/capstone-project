# AI usage log

## Assistance used

Codex helped turn the capstone brief into the initial design, API, provider interface, mismatch guard, generated demo corpus, dashboard, and documentation. It also suggested the deterministic offline fixture provider so evaluators can reproduce the acceptance flow without paid accounts or local model downloads.

## What needed judgment and correction

- The supplied PDF title and requirements did not match the existing repository's earlier lead-capture README/history. The implementation follows the PDF's image-matching capstone. The existing history was preserved and is disclosed in the README; a separate public repository is still required by the brief.
- Fixture tags can demonstrate validation and the refusal workflow, but they cannot establish broad visual understanding. The dashboard and README label the demo provider honestly. Actual model inference is available through NVIDIA NIM, Gemini API, or optional local Ollama. A direct live NVIDIA call using `z-ai/glm-5.3-flash` classified the labeled fox illustration and passed the output schema. The first response used a Markdown JSON fence, so I added tolerant fence removal before schema validation; the repeat call succeeded. This is a smoke check, not a photo accuracy evaluation.
- A deterministic hashed embedding with a small synonym map is not a general semantic model. It is bounded to repeatable capstone probes; for broader language behavior, use Gemini or the local embedding provider and measure its quality on the labeled set.

## Ownership reflection

I reviewed each route, table, and guard rule against the capstone probes. I can explain the processing flow: image classification is validated by `ImageTags`, embeddings share a vector space, candidates are ranked, and `guard()` independently refuses low-confidence or mismatched candidates before they are offered. SQLite stores the run state and each provider operation's cost and attribution. I reran the labeled evaluation, verified the upload endpoint, and completed one live NVIDIA classifier call; `EVIDENCE.md` records those outputs and their limits. Before submission, I still need to publish the project to the dedicated public repository required by the brief.
