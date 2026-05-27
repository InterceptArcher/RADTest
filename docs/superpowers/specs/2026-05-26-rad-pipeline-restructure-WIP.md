---
status: WIP (mid-brainstorm — design not yet approved, spec not locked)
date_started: 2026-05-26
topic: RAD pipeline restructure — Gamma→PPTX swap + BI consolidation
session_id: TBD on resume
---

# RAD Pipeline Restructure — Brainstorm Handoff

> **Resumption note for the next session:** This is a paused brainstorm, not a locked spec. We finished exploration + clarifying questions + approach proposal. We did NOT yet walk through detailed design sections (architecture, components, data flow, error handling, testing) section-by-section with user approval. After this hands off, pick up at the **"Resume here"** section near the bottom.

---

## Goals (from user)

Two coupled restructuring efforts on the RAD pipeline:

**(a) Slideshow generation pipeline — replace Gamma API with a Claude PPTX flow.**
Gamma has been too inconsistent despite multiple rounds of template tweaks, prompt revisions, and the v3 migration. The user wants to leverage the Anthropic Claude "pptx skill" pattern (HTML-style content authoring, but constrained to a user-provided master `.pptx` template) for deterministic visual consistency every time.

**(b) Business intelligence pipeline — consolidate accumulated bandaid layers.**
The ZoomInfo + Apollo + PDL + Hunter integration has acquired many silent fallback layers. Two specific pain points: (1) small/private companies where ZoomInfo coverage is thin and the pipeline silently returns near-empty results; (2) rebranded companies where the user's query name doesn't match ZoomInfo's record because the company changed names.

---

## What I found in exploration

### Current Gamma pipeline (to be replaced)

- **Entry:** `backend/production_main.py:process_company_profile` step 6 (~line 2510) calls `generate_slideshow()` → `GammaSlideshowCreator.create_slideshow()` in `backend/worker/gamma_slideshow.py` (~2961 lines).
- **Flow:** validated_data dict → `_generate_markdown` (formats LLM Council output into Gamma's template-binding markdown) → POST to `gamma.app/v1.0/generations/from-template` with template ID `g_uost7x0lutmwtwd` → poll up to 300 attempts (10 min) → extract URL via 9 fallback strategies.
- **Bandaids built around Gamma:** pending-status handoff, `_spawn_slideshow_reconcile` background task, `_lazy_reconcile_slideshow_if_pending` on `/job-status` reads, 9-strategy URL extractor (`_extract_url`), retry endpoint `POST /api/generate-slideshow/{job_id}`.
- **Frontend touches:** `frontend/src/types/index.ts:52` (`slideshow_url`), `frontend/src/app/dashboard/jobs/[jobId]/page.tsx:401-423` (View Slideshow button), `frontend/src/hooks/useJobs.tsx` localStorage handling.
- **Tests:** 14 test files (9 in `backend/`, 5 in `backend/tests/`) assert Gamma behavior. All to be deleted on cutover.
- **Env vars:** `GAMMA_API_KEY` in `render.yaml:30`, `render-production.yaml:21`, validated at startup in `production_main.py:314`.
- **Template ID:** hardcoded `"g_uost7x0lutmwtwd"` (v3) in `gamma_slideshow.py:52`.
- **Auxiliary:** `backend/worker/main.py` imports `GammaSlideshowCreator` for batch path; `backend/content_audit.py` is consumed by Gamma for collateral matching.

### Current BI pipeline (gaps)

Pipeline: `intelligence_gatherer.py` runs Apollo + PDL + ZoomInfo in parallel; ZoomInfo wins by hardcoded priority regardless of result quality.

Specific gaps identified:

1. **`zoominfo_client.py:1055-1125` — silent 7-level fallback chain.** C-level (`mgmtLevel`) → priority C-suite (`jobTitle`) → other C-suite → VP → Director → no-filter → company-name-only. Falls back to global geo if NA returns 0. No telemetry on which strategy fired.
2. **`zoominfo_client.py:1039-1051` — NA→global silent fallback** for geography.
3. **No company-resolution step.** If user enters "Acme Inc" but ZoomInfo's record is "Acme Tech Co," ZoomInfo enrich returns nothing. Pipeline never tries `companySearch` to surface candidates.
4. **No cross-source name reconciliation.** When ZoomInfo/Apollo/PDL return different names for the same entity, all three results get dumped on LLM Council to figure out.
5. **`data_validator.py:21-196` — `KNOWN_COMPANY_FACTS` covers only 15 hardcoded major tech companies.** Zero pre-validation for SMB/private/non-tech.
6. **`news_gatherer.py` (GNews) — fully wired but never called from the pipeline.** Dead code.
7. **`hunter_client.py:158-175` — only verifies pre-existing emails, never proactively finds missing ones.**
8. **No `data_quality_score` surfaced.** A job built off 1 fallback-strategy contact looks identical to one with 20 high-confidence contacts.
9. **Hardcoded source priority** regardless of result quality (ZoomInfo wins even if Apollo returned 5x more contacts).
10. **LLM Council carries slide-specific formatting concerns** (no-SKU constraint, account-type bucketing, opportunity formatting) — renderer leaking into validator, the root cause of v3 brittleness.

---

## Clarifying questions asked & user's answers

| # | Question | User's answer |
|---|----------|---------------|
| 1 | PPTX format approach | Anthropic pptx skill **+** user-provided `.pptx` master template (mix of HTML-skill pattern and python-pptx mechanical fill) |
| 2 | Slide structure (fixed vs dynamic) | **Fixed N slides, exactly mirror current Gamma deck** (incl. up to 4 stakeholder profile slides via canonical picker) |
| 3 | Where the .pptx lives | **Supabase Storage with public URL** (frontend swaps "View Slideshow" to a Download link) |
| 4 | Migration strategy | **Hard cutover** — delete Gamma in the same PR (gamma_slideshow.py, 14 test files, GAMMA_API_KEY, polling/reconcile machinery all removed) |
| 5 | BI scope | **Full consolidation, with rebrand + small-co as the focal points** (combination of "top 5 surgical" and "full rewrite" options) |
| 6 | Rebrand detection mechanism | **Preliminary ZoomInfo company-search/match step** to surface candidates → disambiguate by domain/industry/geo/headcount → **Claude web search reconciliation ONLY when genuinely ambiguous** (multiple plausible candidates OR top candidate name diverges from user input) |
| 7 | Small-company strategy | **Cascade**: source-switching to Apollo/PDL on ZI zero-result + Hunter.io augmentation + **Claude web search worst-case** (browses LinkedIn / company website for intel) |
| 8 | Authoring boundary (where Claude composes copy) | **Option 2 (recommended by Claude, confirmed by user)** — LLM Council = validator only (no formatting), Claude formatting pass = slide copy authoring, python-pptx = mechanical template fill. User's framing: "LLM Council should be more of a data validation layer as opposed to a formatting bot." |

---

## Approaches proposed

### Approach A — "Three Boxes" *(Claude's recommendation, user has not yet approved)*

```
[ BI Resolver ] → [ LLM Council validator ] → [ Claude formatting pass ] → [ PPTX renderer ]
     |                    |                              |                          |
  Resolves           Fact validation               Slide copy                 Mechanical
  company,           (no formatting)               authoring                  template fill
  contacts,                                        (per slide)                (python-pptx)
  signals
```

**BI Resolver** (replaces `intelligence_gatherer.py` + most of `zoominfo_client.py` surface):

1. **Company-resolution step before any enrichment.** ZoomInfo `companySearch` → candidate list → score candidates (domain match strongest, then industry + geography + employee bucket).
   - If 1 clean candidate → proceed.
   - If multiple plausible candidates OR top candidate's name diverges from user input by edit-distance threshold → invoke Claude web search reconciliation ("is `<user_input>` the same company as `<zi_candidate>`?"). Cache result on the company record.
2. **Source cascade with explicit zero-result switching:**
   - ZoomInfo (now correctly resolved) → if `<2` contacts, Apollo → if still `<2`, PDL → if still empty, Hunter.io `domain-search` → worst case, Claude web search for LinkedIn/company-site intel.
3. **Telemetry on every step.** Which strategy fired, what was returned, what was discarded. Surfaces as `enrichment_trace` in result for debugging + UI badge.
4. **Hunter.io promoted to proactive email-finder** for any contact missing an email (today only verifies pre-existing emails).
5. **`data_quality_score` (0–1)** computed from source reliability, fallback depth, cross-source agreement. Surfaced on dashboard as High/Medium/Low confidence badge.
6. **GNews wired up** as a parallel intelligence signal feeding `news_intelligence` AND the rebrand detector (search for `"<company> renamed"`, `"acquired"`, etc.).

**LLM Council validator** — keeps the 20-specialist consensus but strips all slide-specific formatting concerns. Output is a pure facts dict: `{company, stakeholders, signals, opportunities, ...}` with no formatting rules embedded.

**Claude formatting pass** — single Claude call per job. Input: validated facts + the master template's slot manifest (what each slide needs). Output: structured JSON with slide-ready copy per slot (`slide_title`, `slide_subtitle`, `bullets[]`, etc.). All copy-level concerns (tone, length, no-SKU constraint, account-type bucketing) live here in one prompt.

**PPTX renderer** — opens master `.pptx` template via python-pptx, walks named placeholders, fills them from the Claude formatting pass output. No LLM, no fallbacks — if a slot is empty, fail loud (better than silent ugly slides). Saves to Supabase Storage, returns public URL.

**Trade-offs:**
- ✅ Cleanest boundaries, easiest to test (each box has a single interface)
- ✅ Three independent units = more files but more focused ones
- ✅ Directly addresses every gap from the exploration
- ✅ Aligns with "skill" pattern: Claude authors copy, template enforces structure
- ❌ Highest LLM cost — three serial calls (Council + formatting + possibly Claude web search). Mitigation: cache web-search reconciliation result by company.
- ❌ Largest PR / blast radius. Hard cutover means no fallback if PPTX regresses.

### Approach B — "Two Boxes" *(not recommended)*

Fuse BI resolver and validator into one expanded LLM Council. Fuse the formatting pass into the renderer.

**Trade-offs:**
- ✅ Fewer moving parts, fewer LLM calls
- ❌ LLM Council prompt gets even bigger and harder to evolve
- ❌ Renderer mixes copywriting with mechanical filling — same concern-leakage that caused v3 brittleness
- ❌ Doesn't deliver the clean validator/formatter split the user explicitly asked for

### Approach C — "Minimal Surgical" *(not recommended)*

Keep `intelligence_gatherer.py` mostly intact. Surgical fixes only: ZoomInfo company-resolution, conflict-only Claude web search, `data_quality_score`, swap `gamma_slideshow.py` for `pptx_renderer.py`.

**Trade-offs:**
- ✅ Lowest risk, smallest PR
- ❌ User explicitly asked for full consolidation — minimal doesn't deliver
- ❌ Leaves silent fallback chains and 7-level ZoomInfo cascade intact
- ❌ Same ZI bandaids stick around

---

## Decisions locked in so far

- ✅ Master `.pptx` template provided by user (not yet handed over — pending)
- ✅ Fixed slide count mirroring current Gamma deck (4 stakeholder slides max via canonical picker)
- ✅ Supabase Storage with public URL for hosted decks
- ✅ Hard cutover — delete Gamma entirely in the same PR
- ✅ Full BI consolidation with rebrand + small-co as focal points
- ✅ Claude web search only on genuine conflict (post company-search disambiguation)
- ✅ Cascade for small companies: ZI → Apollo → PDL → Hunter → Claude web search
- ✅ Approach 2 boundary: LLM Council = validator only, Claude = formatter, python-pptx = renderer
- 🟡 **Approach A as the architecture — Claude recommended, user has NOT yet given explicit approval** (this is where we paused)

---

## Resume here (when picking back up)

### Brainstorm checklist status

| # | Step | Status |
|---|------|--------|
| 1 | Explore project context | ✅ Done |
| 2 | Ask clarifying questions one at a time | ✅ Done (8 questions, answers in table above) |
| 3 | Propose 2-3 approaches | ✅ Done (A, B, C laid out above) |
| 4 | Present design sections, get approval | ⏸ **NOT STARTED** — user needs to approve Approach A first, then walk through detailed sections (architecture, components, data flow, error handling, testing) section-by-section |
| 5 | Write design doc to `docs/superpowers/specs/2026-05-26-rad-pipeline-restructure-design.md` | ⏸ Pending |
| 6 | Spec self-review + user review | ⏸ Pending |
| 7 | Hand off to writing-plans skill | ⏸ Pending |

### Specific next-session actions

1. **Confirm Approach A** (or pivot). If user wants a different approach, redo step 3.
2. **Receive the master `.pptx` template from the user** — needed to inventory slot names, infer placeholder structure, and decide whether the renderer reads layout via python-pptx introspection or via an out-of-band slot manifest.
3. **Walk through detailed design sections** with the user, getting approval after each:
   - **Architecture diagram** — the four units (BI Resolver, LLM Council validator, Claude formatting pass, PPTX renderer) and their interfaces
   - **Component details** — for each unit: what it does, what it consumes, what it produces, where it lives in the repo. Include the new files (`bi_resolver.py`, `pptx_renderer.py`, `claude_formatter.py`) and what gets deleted (`gamma_slideshow.py`, `intelligence_gatherer.py` if fully replaced)
   - **Data flow** — request lifecycle from `POST /profile-request` through to `slideshow_url` on the job result. Include the new `enrichment_trace`, `data_quality_score`, and rebrand-resolution paths.
   - **Error handling** — fail-loud on empty slots (PPTX renderer), telemetry on degraded paths (BI resolver), Claude web search caching/circuit-breaker.
   - **Testing** — what gets replaced (14 Gamma tests, several BI tests), what gets added (pptx golden-file tests, BI resolver cascade tests, rebrand-resolution tests).
4. **Resolve open design questions** (listed below).
5. **Write the locked spec** to `docs/superpowers/specs/2026-05-26-rad-pipeline-restructure-design.md`.
6. **Hand off to writing-plans skill.**

### Open design questions to settle

- **Master template slot manifest format.** Does python-pptx introspect placeholder names directly, or do we maintain a separate `slot_manifest.json` mapping slot names to slide indices? The latter is more explicit but adds a sync burden.
- **What happens to `content_audit.py`?** Today Gamma consumes it for collateral matching. Does it move to the Claude formatting pass, the renderer, or stay where it is and get pulled in by Claude?
- **Cache key for Claude web search rebrand reconciliation.** By `(user_input_name, primary_domain)`? By company UUID once persisted? Cache TTL?
- **Data quality score thresholds.** What numeric ranges map to High / Medium / Low confidence on the badge?
- **Claude model for the formatting pass.** Sonnet 4.6? Haiku 4.5 for cost? Opus for quality on edge cases?
- **GNews integration shape.** Always-on parallel call, or only triggered on rebrand-suspect cases?
- **Backwards compat on `slideshow_status` field.** Drop it (PPTX is synchronous) or keep it for frontend compatibility?
- **Existing `/api/generate-slideshow/{job_id}` retry endpoint.** Adapt it to PPTX or delete it (Gamma's polling/reconcile machinery goes away with cutover)?
- **Where does the salesperson_name attribution live in the new flow?** Today it's passed through several layers — likely consumed by the Claude formatting pass.

### Reference: locked decisions

(See "Decisions locked in so far" section above. These should not be revisited without explicit user override.)
