# Knowledge

This repo's knowledge lives in a sibling knowledge base (its own git repo, provenance-first):

- **KB**: `../Open-Game-Standards-Knowledge/` (relative to this repo's root)
- **Contract**: [`../Open-Game-Standards-Knowledge/schema/AGENTS.md`](../Open-Game-Standards-Knowledge/schema/AGENTS.md)

Architecture: sources are captured immutably and content-addressed in the KB's `raw/`; claims in its `wiki/` cite line-level spans of those sources (never drifting copies); indexes and wiki pages are disposable, rebuildable artifacts. Findings about this repo (schema evolution, design decisions) are filed there as claims with provenance — not as extra docs inside this repo. Application source must never be mixed into the knowledge layers.
