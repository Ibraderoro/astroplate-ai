# README Update Plan

## Top-Level Overview

The current `README.md` is missing three of the five required sections for a
public submission README:

1. **Problem Statement** — the problem context is blended into the Overview but
   never framed as a dedicated, standalone statement.
2. **Challenge Theme** — completely absent; the theme is
   *"Space & Astronomy — making astrophotography data accessible and
   interpretable through AI"*.
3. **AI Approach and Architecture** — details are scattered across the Overview
   and Tech Stack prose but there is no dedicated, structured section.

The plan adds these three new top-level sections near the top of the file
without touching or removing any existing content.

---

## Sub-Tasks

---

### Sub-Task 1 — Add "Problem Statement" section

**Intent**
Surface a clear, standalone problem statement so readers immediately understand
*why* the project exists before reading the solution.

**Expected Outcomes**
- A `## 🔭 Problem Statement` heading is present near the top of `README.md`
  (after the tagline blockquote, before `## 🌟 Overview`).
- The section explains, in 2–4 sentences, that raw astrophotography frames are
  difficult to interpret without specialist expertise, that satellite streak
  contamination is hard to identify, and that multi-level scientific
  communication of sky-field data is a barrier to access.

**Todo List**
1. In `README.md`, insert the new `## 🔭 Problem Statement` section immediately
   after the opening blockquote (`> **Astrometric plate-solving…**`) and before
   the `## 🌟 Overview` heading.

**Relevant Context**
- Current line 6 is the blank line after the blockquote; `## 🌟 Overview`
  begins at line 8.
- Insert between those two lines.

**Status:** [x] done

---

### Sub-Task 2 — Add "Selected Challenge Theme" section

**Intent**
Explicitly state the hackathon/challenge theme the project addresses.

**Expected Outcomes**
- A `## 🏆 Selected Challenge Theme` heading is present in the README.
- The section names the theme: *Space & Astronomy* and gives a one-sentence
  description of how the project addresses it.

**Todo List**
1. Insert `## 🏆 Selected Challenge Theme` immediately after the new Problem
   Statement section (before `## 🌟 Overview`).

**Relevant Context**
- Theme confirmed by user: "Space & Astronomy — addressing the challenge of
  making astrophotography data accessible and interpretable through AI".

**Status:** [x] done

---

### Sub-Task 3 — Add "AI Approach and Architecture" section

**Intent**
Give a structured, dedicated explanation of the AI design: what model is used,
how the pipeline feeds context into it, the three-tier prompt strategy, and the
SSE streaming delivery mechanism. This is distinct from the tech-stack bullet
list and the high-level overview.

**Expected Outcomes**
- A `## 🤖 AI Approach and Architecture` heading is present in the README.
- The section covers:
  - The IBM Granite model used (`ibm/granite-13b-chat-v2` via `ibm-watsonx-ai`)
    and why it was selected.
  - How pipeline telemetry (WCS coordinates, star count, satellite NORAD IDs,
    altitude) is assembled into a structured context string and passed as a
    prompt.
  - The three-tier prompt strategy: Kid / Adult / Astrophysicist — one
    `generate_text()` call per tier, each with a tier-specific instruction
    framing.
  - The Server-Sent Events (SSE) streaming architecture: the FastAPI
    `StreamingResponse` emits `progress` events for each pipeline stage, then a
    final `complete` event with the full `AnalyzeResponse` payload.
  - The fault-tolerant `_generate_dynamic_fallback` path for zero-downtime
    offline demos.

**Todo List**
1. Insert `## 🤖 AI Approach and Architecture` immediately after
   `## 🏆 Selected Challenge Theme` (before `## 🌟 Overview`).

**Relevant Context**
- Existing `## 🤖 Built With Bob` section must remain untouched and distinct —
  it covers *Bob (the IBM AI coding assistant)*, not the *Granite model
  architecture*.
- Relevant implementation: `backend/services/granite_explainer.py`.

**Status:** [x] done

---

## Implementation Notes

- All three sub-tasks touch only `README.md`.
- Changes are pure insertions — no existing content is removed or reordered.
- Sub-Tasks 1, 2, and 3 are sequential because each new section is inserted
  directly above `## 🌟 Overview`; complete them in order so line numbers
  remain predictable.
- After all three sections are inserted, verify the final README order is:
  1. Title + tagline
  2. Problem Statement
  3. Selected Challenge Theme
  4. AI Approach and Architecture
  5. Overview (existing)
  6. … all other existing sections unchanged …
