# RAD Pipeline Restructure — Full Design (v3)

**Date started:** 2026-05-26
**Date finalized:** 2026-05-27
**Status:** Approved — ready for implementation plan
**Scope:** Slideshow generation pipeline (Gamma → PowerPoint), business-intelligence consolidation (per-role surgical contact pipeline), region filter, centralized job logging, live-progress dashboard
**Author:** Brainstorm collaboration — user + Claude
**Supersedes:** `2026-05-26-rad-pipeline-restructure-WIP.md`
**Companion (stakeholder summary):** `2026-05-26-rad-pipeline-restructure-overview.md`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Document History](#document-history)
3. [Context & Motivation](#context--motivation)
4. [Goals & Non-Goals](#goals--non-goals)
5. [Architecture Overview](#architecture-overview)
6. [Stage 1 — Company Resolution](#stage-1--company-resolution)
7. [Stage 2 — General Intelligence](#stage-2--general-intelligence)
8. [Stage 3 — Surgical Contact Pipeline](#stage-3--surgical-contact-pipeline)
9. [Stage 4 — LLM Council Validator](#stage-4--llm-council-validator)
10. [Stage 5 — Claude Formatter](#stage-5--claude-formatter)
11. [Stage 6 — PPTX Renderer](#stage-6--pptx-renderer)
12. [Backend — Logging & Live Progress](#backend--logging--live-progress)
13. [Frontend — New Components & Live View](#frontend--new-components--live-view)
14. [Error Handling](#error-handling)
15. [Testing Plan](#testing-plan)
16. [Red-Team Analysis & Mitigations](#red-team-analysis--mitigations)
17. [Trade-offs & Alternatives Evaluated](#trade-offs--alternatives-evaluated)
18. [Migration / Cutover Plan](#migration--cutover-plan)
19. [Open Items](#open-items)
20. [Locked Decisions Reference](#locked-decisions-reference)
21. [Appendix A — Prior Session Clarifying Q&A](#appendix-a--prior-session-clarifying-qa)
22. [Appendix B — This Session Clarifying Q&A](#appendix-b--this-session-clarifying-qa)
23. [Glossary](#glossary)

---

## Executive Summary

The RAD pipeline today has two structural problems that have proven impossible to fix with incremental patches. First, the Gamma slideshow service produces inconsistent visual output despite three rounds of template work, prompt revisions, and the v3 migration. Second, the business-intelligence pipeline has accumulated silent fallback layers across ZoomInfo, Apollo, PDL, and Hunter that cause the system to (a) silently return near-empty results for small or private companies, (b) silently return the wrong company entirely when a target has rebranded or has a regional subsidiary, and (c) pick "the contact with the most-complete data record" rather than "the right person for this role." The combination produces decks that look great but contain the wrong people, or decks that visually drift between runs.

This restructure replaces both subsystems while keeping intact everything that already works (templates, resource recommendations, general firmographics, the LLM Council validator, the salesperson attribution flow). On the slideshow side, Gamma is removed entirely and replaced with a python-pptx renderer driven by a user-controlled master `.pptx` template, with a single Sonnet 4.6 formatting pass authoring the slide copy. On the BI side, the existing parallel-pull-then-sort pattern is replaced with a per-role surgical contact pipeline that mirrors a salesperson's manual workflow: for each of CTO/CFO/CIO/COO, walk a cascade by corporate proximity (C-suite exact → C-suite adjacent → VP → Director, across ZoomInfo → Apollo → PDL → web search), enrich each candidate via cross-source fill plus Haiku 4.5 LinkedIn validation, and advance to the next candidate only if the current one cannot be completed. The deck's stakeholder section becomes a fixed four slides, one contact per role bucket, with the full contact catalogue surfaced separately on the dashboard.

A region-filter checkbox is added for international subsidiaries. Centralized per-job logging persists every job's debug trail to Supabase. A new live-progress dashboard lets the user watch a job run in real time and lets devops diagnose failures without local reproduction. The cutover is a hard one — Gamma is deleted in the same release.

Estimated per-job cost rises from ~$0.10 to ~$0.15–$0.50 (Haiku enrichment + the occasional Stage 3 fallback agent). Estimated job latency changes by +5–15s in the typical case, with cache hits running faster and small-company cases running similar to or faster than today (because the cascade short-circuits early instead of spamming queries).

---

## Document History

This spec is the result of two brainstorming sessions plus a red-team review:

- **2026-05-26 (Session 1).** Initial exploration of the Gamma slideshow problems and the BI silent-fallback problems. Eight clarifying questions answered, three approaches (A "Three Boxes" / B "Two Boxes" / C "Minimal Surgical") proposed. Session paused at the approach-confirmation gate. Findings captured in the WIP doc that this design supersedes.
- **2026-05-27 (Session 2).** Resumed brainstorm. User pivoted from the original "Three Boxes" BI Resolver toward a fundamentally reshaped Stage 3 — surgical per-role contact pipeline mirroring the manual research workflow. Architecture locked in. Detailed component, data-flow, error-handling, and testing sections walked through. Red-team analysis surfaced 12 distinct failure modes; 11 were accepted as mitigations into v3 (the feature-flag rollback path was rejected in favor of hard cutover). Agentic-vs-procedural trade-off evaluated; hybrid pattern adopted (procedural hot path + agentic Stage 3 final-fallback only). Logging and live-progress dashboard added to v3 scope.

All clarifying questions from both sessions are preserved verbatim in Appendices A and B.

---

## Context & Motivation

### Problem 1: Gamma inconsistency

The current slideshow pipeline calls the Gamma API with a user-provided template ID (`g_uost7x0lutmwtwd`, the v3 template added 2026-03-20) and an LLM-generated template-binding markdown. Gamma re-interprets the binding fresh on each render, which means:

- Identical inputs produce visually different decks (slide ordering, font sizes, image placement drift)
- The template-binding markdown grew complex enough that small content changes (e.g., long stakeholder names, embedded apostrophes, certain symbols) regressed slide layouts
- Generation failures produce ambiguous status responses, requiring a 9-strategy URL extractor and a polling-with-reconcile background task to recover
- Three iterations of template tweaks and prompt revisions have not resolved the inconsistency

The Gamma surface in the codebase comprises:

- `backend/worker/gamma_slideshow.py` — 2961 lines
- `backend/production_main.py` Step 6 (~line 2510) — invocation
- Polling machinery: `_spawn_slideshow_reconcile`, `_lazy_reconcile_slideshow_if_pending`, 9-strategy `_extract_url`
- Retry endpoint: `POST /api/generate-slideshow/{job_id}`
- Frontend: `frontend/src/types/index.ts:52` (`slideshow_url`), `jobs/[jobId]/page.tsx:401-423` ("View Slideshow"), `useJobs.tsx` localStorage handling
- 14 test files (9 in `backend/`, 5 in `backend/tests/`)
- Environment: `GAMMA_API_KEY` in `render.yaml:30`, `render-production.yaml:21`, validated at startup in `production_main.py:314`

### Problem 2: BI pipeline silent fallbacks & contact mismatching

The intelligence-gathering side has accumulated bandaid logic that hides failure modes rather than addressing them. Specific gaps surfaced during exploration:

1. **`zoominfo_client.py:1055-1125` — silent 7-level fallback chain.** C-level (`mgmtLevel`) → priority C-suite (`jobTitle`) → other C-suite → VP → Director → no-filter → company-name-only. Falls back to global geo if NA returns 0. No telemetry on which strategy fired.
2. **`zoominfo_client.py:1039-1051` — NA→global silent fallback** for geography.
3. **No company-resolution step.** If user enters "Acme Inc" but ZoomInfo's record is "Acme Tech Co", ZoomInfo enrich returns nothing. Pipeline never tries `companySearch` to surface candidates.
4. **No cross-source name reconciliation.** When ZI/Apollo/PDL return different names for the same entity, all three results get dumped on LLM Council to figure out.
5. **`data_validator.py:21-196` — `KNOWN_COMPANY_FACTS` covers only 15 hardcoded major tech companies.** Zero pre-validation for SMB/private/non-tech.
6. **`news_gatherer.py` (GNews) — fully wired but never called from the pipeline.** Dead code.
7. **`hunter_client.py:158-175` — only verifies pre-existing emails, never proactively finds missing ones.**
8. **No `data_quality_score` surfaced.** A job built off 1 fallback-strategy contact looks identical to one with 20 high-confidence contacts.
9. **Hardcoded source priority** regardless of result quality (ZoomInfo wins even if Apollo returned 5× more contacts).
10. **LLM Council carries slide-specific formatting concerns** (no-SKU constraint, account-type bucketing, opportunity formatting) — renderer leaking into validator.
11. **"Most complete record" wins over "right person for the role."** Today's pipeline pulls many contacts then sorts by data-completeness, often surfacing the wrong title for a slide.
12. **Multinational subsidiary handling.** Querying "Acme Canada" against an entity that exists only as "Acme Inc" globally returns either nothing (if subsidiary entity doesn't exist) or all-global contacts (if it does), with no user control.

### Problem 3: Operational blindness

Two operational issues compound the above:

- **Jobs are stored per-seller.** A devops engineer trying to triage a failure must run the job locally or get the original seller to share their job ID. There is no central log.
- **Running jobs are a black box.** The frontend shows "running…" and the user waits with no insight into which stage is in progress, what data has been pulled, or whether a stage is stuck. Triage on long-running or hung jobs requires reading server logs.

---

## Goals & Non-Goals

### Goals

1. **Eliminate Gamma.** Replace with a deterministic `.pptx` rendering pipeline driven by a user-controlled master template.
2. **Surgical contact pipeline.** Every deck has exactly 4 stakeholder slides (CTO, CFO, CIO, COO), each populated with a real, fully-enriched contact picked by corporate proximity to the role.
3. **Eliminate silent fallback chains.** Every degraded path emits a trace entry; users and devops can see exactly what happened.
4. **Region filter** for multinational subsidiaries (Canada-only checkbox in v3, generalizable later).
5. **Central logging.** Every job (regardless of seller) persists a debug log to Supabase.
6. **Live progress dashboard.** Users can click into a running job and see stage / step / partial data / logs in real time.
7. **Cost discipline.** Average per-job cost stays under $0.50 with the new pipeline.
8. **Latency discipline.** Average job latency increases by no more than ~15 seconds; small-company cases match or improve over today.
9. **Hard cutover.** Gamma code, environment variables, tests, and frontend touchpoints all removed in the same release. No long-lived dual-renderer state.

### Non-Goals

- **Re-designing slide content / template layout.** The new PPTX deck mirrors the existing Gamma deck visually. Master template is provided by the user.
- **Replacing the LLM Council.** The 20-specialist validator stays, with formatting concerns stripped out.
- **Replacing existing structured-data clients.** ZI, Apollo, PDL, Hunter clients keep their existing HTTP surfaces — only their cascading wrappers are removed.
- **Generalized region filter** beyond Canada (deferred — checkbox is structured so it can become a dropdown in a follow-up).
- **A separate logging service.** Logs go to Supabase, not Datadog / Logflare / etc.
- **Server-Sent Events for live progress.** Polling is used instead (simpler, robust on Render's free tier).
- **Salesperson-facing job sharing / collaboration UI.** Out of scope.

---

## Architecture Overview

The new pipeline has **six stages**, plus cross-cutting **logging** and **live-progress** infrastructure. Stages 2 and 3 run in parallel after Stage 1 completes; Stages 4–6 are sequential.

```
                         POST /profile-request
                                  │
                                  ▼
              ┌────────────────────────────────────────┐
              │ Stage 1 — Company Resolution           │
              │   Parallel: ZI + Apollo + PDL + Hunter │
              │   Haiku 4.5 reconciler picks canonical │
              │   Claude web search on ambiguity       │
              └─────────────────┬──────────────────────┘
                                │
                  ┌─────────────┴─────────────┐
                  ▼                           ▼
        ┌──────────────────────┐    ┌────────────────────────────────────┐
        │ Stage 2 —            │    │ Stage 3 — Surgical Contact Pipeline│
        │ General Intelligence │    │                                    │
        │ ZI + Apollo + PDL +  │    │ For each role ∈ {CTO,CFO,CIO,COO}: │
        │ GNews (parallel)     │    │  Cascade: ZI tiers → Apollo → PDL  │
        │                      │    │  Enrich: cross-fill + Haiku web    │
        │                      │    │  Advance on incompleteness         │
        │                      │    │  Final fallback: agentic search    │
        └──────────┬───────────┘    └─────────────┬──────────────────────┘
                   │                              │
                   └──────────────┬───────────────┘
                                  ▼
              ┌────────────────────────────────────────┐
              │ Stage 4 — LLM Council Validator        │
              │   Facts-only; no formatting rules      │
              │   Receives slide_contacts[4] only      │
              └─────────────────┬──────────────────────┘
                                ▼
              ┌────────────────────────────────────────┐
              │ Stage 5 — Claude Formatter (Sonnet 4.6)│
              │   Single call; slide copy authoring    │
              └─────────────────┬──────────────────────┘
                                ▼
              ┌────────────────────────────────────────┐
              │ Stage 6 — PPTX Renderer (python-pptx)  │
              │   Mechanical fill of master template   │
              │   Uploads to Supabase Storage          │
              └─────────────────┬──────────────────────┘
                                │
                                ▼
              UPDATE profile_requests SET
                slideshow_url, contact_catalogue,
                enrichment_trace, data_quality_score
                                │
                                ▼
              GET /job-status/{id} → frontend dashboard
```

Cross-cutting: a `JobLogger` instance is created at Stage 1 entry and threaded through every stage. It buffers structured log entries and flushes to `profile_requests.debug_logs` at each stage boundary and on completion / failure. Each stage also updates `current_stage`, `current_step`, `step_progress`, `partial_results` columns for the live-progress view to poll.

### Five new files

- `backend/worker/bi_resolver.py` — replaces `intelligence_gatherer.py` and the cascading wrappers in `zoominfo_client.py`. Hosts Stages 1–3.
- `backend/worker/claude_formatter.py` — Stage 5.
- `backend/worker/pptx_renderer.py` — Stage 6. Replaces `gamma_slideshow.py` entirely.
- `backend/worker/job_logger.py` — JobLogger + PII redaction.
- `backend/worker/stage3_fallback_agent.py` — Stage 3 final-fallback Claude agent with tools (`linkedin_search`, `crunchbase_search`, `company_website_scrape`, `news_search`).

### Files modified

- `backend/production_main.py` — `process_company_profile` re-shaped to call the new stages; Gamma machinery removed.
- `backend/llm_council.py` — formatting rules stripped from prompts; input surface narrowed.
- `backend/worker/zoominfo_client.py` — silent fallback chains removed; HTTP client surface kept.
- `backend/worker/apollo_client.py` — `companySearch` added if not already present; bulk pull cascade removed.
- `backend/worker/pdl_client.py` — same shape as Apollo.
- `backend/worker/hunter_client.py` — `domainSearch` for proactive email finding (not just verification).
- `backend/worker/news_gatherer.py` — wired into Stage 2 (previously dead code).
- `backend/main.py` — Gamma slideshow batch path removed; new pipeline imported.
- `frontend/src/types/index.ts` — `slideshow_url` type updated, `slideshow_status` removed, new fields added.
- `frontend/src/app/dashboard/jobs/[jobId]/page.tsx` — "View Slideshow" → "Download Deck (.pptx)", `<ConfidenceBadge />` added, optional debug drawer.
- `frontend/src/app/dashboard/jobs/[jobId]/live/page.tsx` — NEW live-progress route.
- `frontend/src/hooks/useJobs.tsx` — drop `slideshow_status` polling logic.
- `frontend/src/app/dashboard/new-request/page.tsx` — add `<RegionToggle canada_only />`.

### Files deleted

- `backend/worker/gamma_slideshow.py` (2961 lines)
- `backend/intelligence_gatherer.py` (if fully subsumed by `bi_resolver.py`)
- All 14 Gamma test files
- `backend/data_validator.py:21-196` `KNOWN_COMPANY_FACTS` block (replaced by Stage 1 resolution)

### Environment variables

- **Removed:** `GAMMA_API_KEY`
- **Added:** `SUPABASE_STORAGE_BUCKET_DECKS` (already provisioned), `ANTHROPIC_API_KEY` (already present), `DEBUG_RAW_LOGS` (boolean, default false)
- **Existing kept:** `ZOOMINFO_USERNAME`, `ZOOMINFO_PASSWORD`, `APOLLO_API_KEY`, `PDL_API_KEY`, `HUNTER_API_KEY`, `GNEWS_API_KEY`

---

## Stage 1 — Company Resolution

### Purpose

Take the user-supplied company name and resolve it to a canonical company record across all four structured data providers, surfacing and resolving ambiguities (multiple plausible candidates, name divergence across providers, subsidiary vs parent confusion) before any contact discovery runs.

### Inputs

- `input_name: str` — user-supplied company name from the new-job form
- `canada_only: bool` — region filter checkbox state (does NOT scope Stage 1 itself; resolution always works against global entities)

### Procedure

1. **Parallel search across all four sources.** Each source's `companySearch` (or equivalent) is invoked with `input_name`:
   - `zoominfo_client.companySearch(input_name)` — returns candidate ZI entities
   - `apollo_client.companySearch(input_name)` — same
   - `pdl_client.companyEnrich(input_name)` — same
   - `hunter_client.domainSearch(input_name)` — derives domain candidates from name
2. **Cache check.** Lookup `claude_resolution_cache` by key `(normalize(input_name), primary_domain_guess)`. If hit and not expired (TTL 30d), short-circuit return cached canonical.
3. **Haiku 4.5 reconciler.** Pass the four candidate sets + `input_name` to Haiku 4.5 with a structured output schema. The reconciler returns:
   - `canonical_company: { name, primary_domain, industry, hq_country, employee_bucket, is_subsidiary, confidence: 0-1 }`
   - `decision_basis: str` — short justification
   - `needs_reconciliation: bool` — true if intra/cross-service ambiguity detected
4. **Reconciliation decision logic.**
   - If `needs_reconciliation == true` OR `confidence < 0.7` (Mitigation 12) → invoke Claude web search reconciliation tool: "is `<input_name>` the same company as `<candidate>`? Return primary domain and justification."
   - Otherwise proceed with Haiku output directly.
5. **Cache write.** Persist final result to `claude_resolution_cache` with TTL 30d.
6. **Subsidiary auto-enforce (Mitigation 8).** If `is_subsidiary == true` AND `canada_only == false`, log a `subsidiary_geo_mismatch` warning and set Stage 3's country filter to `hq_country` of the resolved subsidiary. Surface a frontend banner: "We detected this is a Canadian subsidiary and filtered contacts accordingly."

### Outputs

- `CanonicalCompany { name, primary_domain, industry, hq_country, employee_bucket, is_subsidiary, confidence }`
- Reconciliation cache hit/miss recorded in `enrichment_trace`

### Failure modes & policy

- All four sources return errors (not just empty) → fail-loud `CompanyResolutionFailedError`. Frontend retry button.
- Haiku 4.5 returns malformed structured output 3× → fail-loud `ResolverOutputInvalidError`.
- Claude web search reconciliation returns ambiguous result → use Haiku's best guess + emit `low_confidence_resolution` warning. Job continues.

---

## Stage 2 — General Intelligence

### Purpose

Gather company-level firmographics, signals, opportunities, recommendations, and news for downstream slide content. **This stage is unaffected by the Canada checkbox** — global company intelligence is still relevant context regardless of which region's contacts are being slide-promoted.

### Inputs

- `canonical: CanonicalCompany` — from Stage 1
- (No `canada_only` parameter)

### Procedure

Largely unchanged from today's `intelligence_gatherer.py`, with these specific changes:

1. **Parallel pulls** of `ZI.enrichCompany`, `Apollo.enrichCompany`, `PDL.companyEnrich`, `GNews.search` for `canonical.name + canonical.primary_domain`.
2. **GNews wired in (Gap 6).** Previously dead code; now an always-on parallel call. **Hard 5-second timeout** (Mitigation 11) — on timeout, news field is empty, rest of intel proceeds, trace records `gnews: timed_out`.
3. **Output merge.** Cross-source merge with explicit conflict logging (which source said what). No silent priority — if ZI says revenue is $50M and Apollo says $200M, both go in the trace and the LLM Council validates.
4. **`KNOWN_COMPANY_FACTS` removed.** The 15-company hardcoded validation list is deleted; Stage 1's canonical resolution + Council validation replaces it.

### Outputs

- `GeneralIntel { firmographics, signals, opportunities, recommendations, news, source_conflicts: [...] }`

### Failure modes & policy

- Any one source fails → degrade-gracefully, log to trace, continue
- All four sources fail → fail-loud `GeneralIntelFailedError` (rare; usually indicates a Stage 1 mis-resolution)

---

## Stage 3 — Surgical Contact Pipeline

This is the most substantial change in v3 and the section that most directly addresses the brittleness in today's pipeline.

### Purpose

For each of the four role buckets (CTO, CFO, CIO, COO), identify the best-fit contact for the slide by walking a corporate-proximity cascade and enriching each candidate procedurally. Move to the next candidate only when the current one cannot be completed. Worst-case fall back to an agentic search; absolute worst case, mark the slide "no contact found."

### Inputs

- `canonical: CanonicalCompany`
- `canada_only: bool` — when true, every cascade query adds `country = Canada` filter

### The mental model

This pipeline mirrors a salesperson's manual research workflow, captured verbatim from Session 2:

> 1. Determining which contact is suitable for the slide — on ZoomInfo under the company, check the contacts under the C-suite filter, looking for a contact with a similar title, if not check VP filter, Director, etc.
> 2. Clicking on their contact in ZoomInfo I get most of the general information — position, email, phone, LinkedIn.
> 3. I google their LinkedIn and there I get more auxiliary information like their start date and usually their profiles exist if they are high standing enough.

### Per-role cascade (Step A — Discovery)

For each role in `[CTO, CFO, CIO, COO]`, walk this cascade in order:

| Tier | Source | Filter |
|------|--------|--------|
| 1 | ZoomInfo | C-suite filter, **exact** title match for the role |
| 2 | ZoomInfo | C-suite filter, **canonical adjacent** titles (e.g., CTO ≈ Chief Engineering Officer, VP of Engineering at C-level) |
| 3 | ZoomInfo | C-suite filter, **LLM-judged adjacent** titles (hybrid fallback for novel titles like "Chief Code Officer") |
| 4 | ZoomInfo | VP filter, role-area match |
| 5 | ZoomInfo | Director filter, role-area match |
| 6 | Apollo | Same tiers 1–5 |
| 7 | PDL | Same tiers 1–5 |
| 8 | **Stage 3 fallback agent** | Agentic Claude loop with tools (see below) |

**Adjacency definition (hybrid; Mitigation per Session 2 Q1):**

- A canonical title list per bucket is maintained in code (e.g., `CTO_BUCKET = {"chief technology officer", "chief engineering officer", "vp of engineering", "vp of technology", "head of engineering", "head of technology", ...}`).
- When ZoomInfo returns a C-suite candidate whose title doesn't match the canonical list, Haiku 4.5 is invoked with the title + the role bucket: "Is `<title>` a reasonable proxy for the `<role>` of this company? Respond yes/no with one-sentence justification." This handles novel/unusual titles without polluting the canonical list.

**Short-circuit (Mitigation 1):** If ZI returns 0 candidates in **both** tier 1 + tier 4 (C-suite filter and VP filter), skip directly to Apollo. Signal: this company's structure simply does not have this role at the senior level. Avoids burning Director-tier and adjacent-title queries on a company that doesn't structurally have a CIO function.

**Region filter:** When `canada_only == true`, every query in tiers 1–7 adds `country = Canada`. The Stage 3 fallback agent (tier 8) receives `country=Canada` as a constraint in its system prompt.

### Per-candidate enrichment (Step B)

For each candidate surfaced by the cascade, before deciding "use this" or "advance," attempt full data completion:

1. **ZI primary record.** Pull `email, phone, position, linkedinUrl, hireDate` (the existing schema in `zoominfo_client.py`).
2. **Cross-fill from other sources** for any missing field. Cross-fill subject to **strong entity match** (Mitigation 2): the source's contact record must match the ZI record on **email OR LinkedIn URL** — name-only match is rejected to prevent the "common-name collision" failure mode.
3. **Haiku 4.5 LinkedIn enrichment.** Always-on (Session 2 decision): Haiku web search on `linkedinUrl` to validate start_date + auxiliary info. Required response schema:
   ```json
   {
     "start_date": "string|null",
     "current_position_confirmed": "bool",
     "extracted_snippet": "string",  // required citation
     "source_url": "string"          // required citation
   }
   ```
   Responses without `extracted_snippet` are rejected (Mitigation 3) — treated as "field not found," not as evidence of presence.

### Completeness criterion

A contact is **complete enough to use on a slide** iff:

- `name` populated
- `title` populated
- `email` populated
- `linkedinUrl` populated
- `start_date` populated

`phone` is **optional** — its absence does not disqualify a contact. (Session 2 user decision: "the only value that can be missing is a phone number sometimes.")

### Per-role decision logic

```
For each role in [CTO, CFO, CIO, COO]:
    candidates = walk_cascade(role, canada_only)  # ordered by proximity
    selected = None
    examined = []
    for candidate in candidates:
        enriched = enrich(candidate)   # ZI + cross-fill + Haiku LinkedIn
        examined.append(enriched)
        if is_complete(enriched):
            selected = enriched
            break
        elif systemic_field_absence_detected(examined):
            # Mitigation 4: same field missing for all examined candidates
            # → treat as company-level issue, accept the most proximate
            selected = examined[0]
            mark_warning("systemic_field_absence: " + missing_field)
            break
    if selected is None:
        # cascade exhausted; fall back to best-of-incomplete
        if examined:
            selected = examined[0]  # most-proximate of incomplete pool
            mark_warning("fell_back_to_incomplete_contact")
        else:
            # truly nothing — invoke Stage 3 fallback agent
            selected = stage3_fallback_agent(role, canonical, canada_only)
            if selected is None:
                selected = "no_contact_found"
                mark_warning("no_contact_found_for_role")

    # Cross-slide dedupe (Mitigation 5)
    if selected.linkedin_url in already_used_linkedins:
        # advance to next candidate in cascade for this slide
        ... (loop logic, fallback to "shared_role" flag if dedupe exhausts cascade)

    slide_contacts[role] = selected
    contact_catalogue[role] = examined  # all candidates including rejected
    enrichment_trace.extend(per-step trace entries)
```

### Stage 3 fallback agent (Tier 8)

When the procedural cascade is fully exhausted (no candidates found in any of ZI / Apollo / PDL for the role), a Claude agent (Haiku 4.5) is invoked with the following tools:

- `linkedin_search(query: str) → results[]` — searches LinkedIn for profiles matching `query`
- `crunchbase_search(company_name: str) → company_profile` — fetches Crunchbase company page with exec team listed
- `company_website_scrape(domain: str, path: str = "/about" or "/team") → html` — fetches About / Team / Leadership page
- `news_search(query: str) → article_snippets[]` — searches news mentions for `<role> of <company>`

Agent system prompt summary: "Your job is to find ONE senior person at `<company>` who is the closest reasonable fit for the `<role>` role. Validate the person actually works there by confirming with at least two sources. Return the contact with as many fields as you can find. If you cannot find anyone, return null. Do NOT fabricate."

Agent runs with a hard turn cap (5 tool calls max) to bound cost. On output, the result is treated like any other cascade candidate: subjected to the same completeness criterion, used if complete, else "no contact found" for this slide.

Estimated cost: $0.20–$0.40 per invocation. Fires on ~5–10% of jobs. Average added cost across all jobs: $0.02–$0.04.

### Worst-case ladder

In order of preference:

1. Complete contact from the cascade (preferred outcome)
2. Best-proximate incomplete contact (cascade exhausted, dropped completeness requirement)
3. "Any employee at company" via Stage 3 fallback agent (cascade exhausted, agent had to search broadly)
4. "No contact found" — slide marker

### Outputs

- `slide_contacts: { CTO: StakeholderRecord, CFO: StakeholderRecord, CIO: StakeholderRecord, COO: StakeholderRecord }` — exactly 4 entries; some may be the `no_contact_found` sentinel
- `contact_catalogue: { CTO: [...], CFO: [...], CIO: [...], COO: [...] }` — all examined candidates per bucket (for the dashboard's debug drawer)
- `enrichment_trace: [{ role, cascade_step, source, candidate_name, outcome }, ...]` — chronological trace
- `data_quality_score: float (0.0–1.0)` — computed from source reliability, fallback depth, cross-source agreement, required field coverage

### `data_quality_score` computation

Weighted score:

- 0.4 × `source_reliability_avg` (ZI=1.0, Apollo=0.85, PDL=0.7, Hunter=0.5, web_search=0.4) averaged across the 4 selected slide contacts
- 0.3 × `cascade_efficiency` (1.0 if all 4 picked from tier 1; decreases monotonically with average tier depth)
- 0.2 × `required_field_coverage` (fraction of `name/title/email/linkedin/start_date` populated across the 4 slide contacts)
- 0.1 × `cross_source_agreement` (fraction of slide contacts where ≥2 sources agreed on email)

**Provisional thresholds for badge:** High ≥ 0.75, Medium 0.4–0.75, Low < 0.4. Tunable in code; will be calibrated against first week of production runs.

---

## Stage 4 — LLM Council Validator

### Purpose

Multi-specialist fact validation of the BI Resolver's output. Returns the same shape it receives, with corrections and confidence flags applied. **No formatting concerns** — all slide-copy-shaping logic is removed from Council prompts in v3.

### Inputs

- `general_intel: GeneralIntel` (Stage 2 output)
- `slide_contacts: { CTO, CFO, CIO, COO }` — **only the 4 slide-selected contacts**, NOT the full `contact_catalogue` (Mitigation 10 — avoids prompt explosion)

### Procedure

Keeps today's 20-specialist consensus structure. Stripped from the Council prompts:

- No-SKU constraint (now lives in Claude Formatter prompt)
- Account-type bucketing (now lives in Claude Formatter prompt)
- Opportunity formatting rules (now lives in Claude Formatter prompt)
- Stakeholder slide composition rules (now lives in Claude Formatter prompt + this stage receives only 4 contacts already)

Kept in Council prompts:

- Fact-accuracy validation (name spelling, title format, signal plausibility, revenue/headcount sanity checks)
- Cross-source agreement validation (when ZI and Apollo disagreed, Council adjudicates)
- Confidence-flag emission per validated field

### Outputs

- `validated_facts: { ...same shape as input, with corrections, plus confidence flags per field }`

### Failure modes & policy

- Council fails entirely (Anthropic API outage / malformed output 3× retries) → fail-loud `CouncilValidationFailedError`. Cannot be degraded-gracefully — without Council validation, downstream slide copy may contain unvetted facts.

---

## Stage 5 — Claude Formatter

### Purpose

Single Sonnet 4.6 call per job. Authors slide-ready copy for each placeholder in the master template. Owns all formatting concerns: tone, length, no-SKU constraint, account-type bucketing, opportunity copy shape, stakeholder slide layout.

### Inputs

- `validated_facts: dict` — Stage 4 output
- `slot_manifest: dict` — extracted at runtime from the master `.pptx` via python-pptx introspection. Format: `{ slide_id: { slot_name: { type: "text"|"bullets"|"image", max_length: int|null, required: bool } } }`

The slot manifest is **introspected dynamically** at render-time from the master template (not maintained as a separate JSON file) — Mitigation 6, to prevent manifest drift.

### Procedure

1. Build the formatter prompt: `system_prompt + facts_block + slot_manifest_block + output_schema`.
2. Single Claude API call (Sonnet 4.6, `temperature=0.2`, prompt cache enabled on the static portions).
3. Validate output JSON against schema: every slot in manifest must be present (or have a documented `null` fallback for non-required slots).
4. If schema validation fails, retry up to 3× with a "fix the malformed JSON" follow-up message.
5. Cache the formatter response by `hash(facts) + hash(slot_manifest)` — useful for re-render scenarios.

### Outputs

- `slide_copy_json: { slide_id: { slot_name: copy_value } }` — keyed exactly to the slot manifest

### Failure modes & policy

- 3 retries fail → fail-loud `FormatterOutputInvalidError`
- Formatter references a slot not in manifest → fail-loud `FormatterSlotMismatchError` (caught at validation stage before rendering)

**Cost:** ~$0.03–$0.08 per job (Sonnet 4.6, with prompt caching).

---

## Stage 6 — PPTX Renderer

### Purpose

Mechanically open the master `.pptx`, fill its named placeholders from the formatter output, save the result to Supabase Storage, return the public URL. No LLM. No retries beyond Supabase Storage upload retries. Fail-loud on any inconsistency.

### Inputs

- `slide_copy_json: dict` — Stage 5 output
- `master_template_path: str` — Supabase Storage URL or local path (configured via `SUPABASE_STORAGE_BUCKET_DECKS` env)
- `job_id: str` — used in the output filename

### Procedure

1. Download master template from Supabase Storage (cached locally per worker instance).
2. `pptx = Presentation(master_template_path)`
3. For each slide in `pptx.slides`:
   - For each named placeholder in the slide:
     - Look up matching slot in `slide_copy_json`
     - If slot is required and value is missing → raise `EmptyRequiredSlotError`
     - If value is present, fill the placeholder. Text slots get plain text; bullet slots get a paragraph list; image slots get an image insertion.
4. Save to a local temp `.pptx`.
5. Upload to Supabase Storage with key `decks/{job_id}.pptx`. Public-read ACL.
6. Return the public URL.

### Outputs

- `slideshow_url: str` — public Supabase Storage URL

### Failure modes & policy

- Master template not present in Supabase Storage → fail-loud `MasterTemplateMissingError`
- Formatter output references a slot not in the template → fail-loud `SlotManifestDriftError` with the mismatched slot name
- Required slot empty after formatter pass → fail-loud `EmptyRequiredSlotError`
- Supabase Storage upload fails → retry 3× with exponential backoff; fail-loud `StorageUploadFailedError` after exhaustion
- python-pptx parsing exception on the master → fail-loud `MasterTemplateCorruptError`

---

## Backend — Logging & Live Progress

### `JobLogger` (`backend/worker/job_logger.py`)

**Purpose:** Centralized per-job structured logger that captures everything the pipeline does, persists to Supabase, and redacts PII by default.

**API:**

```python
class JobLogger:
    def __init__(self, job_id: str, redact_pii: bool = True): ...
    def write(self, *, stage: str, step: str, level: Literal["info","warn","error"], msg: str, data: dict | None = None): ...
    def flush(self) -> None: ...  # writes buffer to profile_requests.debug_logs (jsonb)
    def __enter__(self): ...
    def __exit__(self, exc_type, exc_val, exc_tb): ...  # flushes on exit, including error context if exception
```

**Behavior:**

- Buffers entries in memory (capped at 5000 entries to prevent runaway memory on stuck jobs).
- Flushes on stage boundaries and on context-manager exit (whether success or exception).
- On flush failure (Supabase write error), logs to stderr and continues. Telemetry must never block job progress.
- **PII redaction** runs in `write()` before buffering:
  - Emails → `j***@acme.com`
  - Phones → `+1-***-***-1234`
  - LinkedIn URLs preserved (not PII-sensitive at the URL level)
  - Names preserved (necessary for debugging)
- `redact_pii=False` only when `DEBUG_RAW_LOGS=true` env is set (dev/staging only).

### Database schema changes

`profile_requests` table additions:

| Column | Type | Notes |
|--------|------|-------|
| `debug_logs` | jsonb | Array of `{ts, stage, step, level, msg, data}` entries |
| `current_stage` | text | "1_resolution" / "2_general" / "3_contacts" / "4_council" / "5_format" / "6_render" / "done" / "failed" |
| `current_step` | text | Free-form sub-step label (e.g., "CFO bucket, Apollo cascade") |
| `current_stage_seq` | int | Monotonic integer for out-of-order update protection |
| `step_progress` | numeric(3,2) | 0.0–1.0 progress within current step |
| `partial_results` | jsonb | Accumulates as stages complete: `{stage1: {...}, stage2: {...}, ...}` |
| `contact_catalogue` | jsonb | Per-bucket arrays of examined candidates |
| `enrichment_trace` | jsonb | Chronological trace from BI Resolver |
| `data_quality_score` | numeric(3,2) | 0.0–1.0 |
| `slideshow_status` | (removed) | — |

`claude_resolution_cache` table (NEW):

| Column | Type | Notes |
|--------|------|-------|
| `cache_key` | text PK | `normalize(input_name) + '\|' + primary_domain` |
| `canonical_company` | jsonb | The resolved CanonicalCompany record |
| `decision_basis` | text | Haiku's justification |
| `created_at` | timestamptz | TTL anchor (30d) |
| `last_hit_at` | timestamptz | For hit-rate analytics |

`linkedin_enrichment_cache` table (NEW):

| Column | Type | Notes |
|--------|------|-------|
| `linkedin_url` | text PK | The URL queried |
| `enrichment` | jsonb | `{start_date, current_position_confirmed, extracted_snippet, source_url}` |
| `created_at` | timestamptz | TTL anchor (7d) |

### Live-progress update pattern

Each stage updates the live-progress columns using a monotonic guard:

```sql
UPDATE profile_requests
SET current_stage = $1, current_step = $2, current_stage_seq = $3,
    step_progress = $4, partial_results = partial_results || $5
WHERE id = $6 AND (current_stage_seq IS NULL OR current_stage_seq < $3);
```

This guards against out-of-order writes (e.g., a slow stage finishing after a faster stage has already advanced the seq).

### Circuit breakers

Per upstream API (ZI, Apollo, PDL, Hunter, GNews, Anthropic):

- 5 consecutive failures in a 60s window → open circuit for 30s
- While open: the source is skipped entirely; cascade moves on
- Breaker state written to `enrichment_trace` so devops can see which upstream was failing

Implementation: `backend/worker/circuit_breaker.py` (new), in-memory per-worker-process state.

---

## Frontend — New Components & Live View

### New components

- **`<RegionToggle canada_only />`** — checkbox on the new-job form. Posts `canada_only: bool` to `POST /profile-request`.
- **`<ConfidenceBadge data_quality_score={...} />`** — colored pill on the job detail page. Maps score to High/Medium/Low with provisional thresholds.
- **`<ContactCatalogue catalogue={...} />`** — collapsible per-bucket view of all candidates examined for each of the 4 roles. Shows the picked candidate at the top, the rejected candidates below with a reason annotation ("missing email," "lower proximity," etc.).
- **`<EnrichmentTraceDrawer trace={...} />`** — debug drawer behind a small "Show details" link on the job detail page. Renders the full chronological enrichment_trace.

### New route: Live Job View (`/dashboard/jobs/[jobId]/live`)

Auto-redirected from the new-job submit flow. Polls `/job-status/{id}` every 2s with backoff on error (2 → 4 → 8s, capped). Three tabs:

1. **Progress** — pipeline stage diagram. The current `current_stage` is highlighted; `current_step` is shown as a sub-label. Each completed stage gets a checkmark. Estimated remaining time shown when computable.
2. **Partial Data** — as stages complete, their outputs render here:
   - Stage 1: canonical company chip ("Acme Inc · acme.com · Manufacturing · USA · 1000–5000 employees")
   - Stage 2: firmographics summary, signals list, opportunities, news headlines
   - Stage 3: contact catalogue filling in as each bucket resolves (with running cascade trace)
   - Stages 4–6: tick-marks only ("Validation complete," "Slide copy authored," "Deck ready")
3. **Logs** — paginated `debug_logs` entries with filters: severity (info/warn/error), stage, and free-text search. Default view: warnings + errors only.

On `current_stage == "done"`: page shows a "Done" state with the Download Deck (.pptx) button, plus a "View details" link to the existing `/jobs/[jobId]` detail page.

On `current_stage == "failed"`: page shows the error code + human message + retry button + the log tab open to the error.

### Existing routes touched

- **`/dashboard/new-request`** — `<RegionToggle />` added.
- **`/dashboard/jobs/[jobId]`** — "View Slideshow" → "Download Deck (.pptx)", `<ConfidenceBadge />` added next to status, `<ContactCatalogue />` rendered in a new section, `<EnrichmentTraceDrawer />` behind a debug link, `slideshow_status` polling removed.
- **`useJobs.tsx`** — `slideshow_status` polling logic deleted.

### Frontend tests

- `<RegionToggle />` posts `canada_only: true` when checked
- `<ConfidenceBadge />` maps `0.8 → High`, `0.5 → Medium`, `0.3 → Low`
- Live view: tab rendering, polling cadence, backoff on connection error, redirect to detail page on completion
- "Download Deck" button uses `slideshow_url` (now Supabase Storage URL, not Gamma URL)

---

## Error Handling

Five categories, each with a clear policy.

### A. Fail-loud (job fails with actionable error)

| Error | When | Frontend surface |
|-------|------|------------------|
| `CompanyResolutionFailedError` | All 4 Stage 1 sources error | "We couldn't find this company in our data sources. Check spelling or try again." |
| `MasterTemplateMissingError` | Stage 6 can't find master `.pptx` | "Master template not configured. Contact admin." |
| `MasterTemplateCorruptError` | python-pptx can't parse master | "Master template is corrupt. Contact admin." |
| `SlotManifestDriftError` | Formatter references a slot not in template | "Template/code mismatch. Contact engineering." |
| `EmptyRequiredSlotError` | Required slide slot empty after formatter | "Slide copy generation incomplete. Retry." |
| `FormatterOutputInvalidError` | Sonnet 4.6 returns malformed JSON 3× | "Slide copy generation failed. Retry." |
| `FormatterSlotMismatchError` | Pre-render slot mismatch | "Template/code mismatch. Contact engineering." |
| `CouncilValidationFailedError` | LLM Council outage / malformed 3× | "Fact validation failed. Retry in a few minutes." |
| `ResolverOutputInvalidError` | Stage 1 Haiku malformed 3× | "Company resolution failed. Retry." |
| `StorageUploadFailedError` | Supabase Storage upload fails after 3 retries | "Deck couldn't be saved. Retry." |
| `GeneralIntelFailedError` | All 4 Stage 2 sources error | "Couldn't gather company intelligence. Retry." |

### B. Degrade gracefully (job continues, trace recorded)

- **GNews timeout (>5s)** — Mitigation 11. News empty; rest of intel proceeds.
- **Haiku LinkedIn transient failure** — retry 2× with exponential backoff. Then null `start_date`, trace `linkedin_web_search: failed_after_retries`. Contact may fall to next in cascade per Mitigation 4.
- **Haiku response lacks citation** — Mitigation 3. Treat as field missing.
- **Cross-fill entity match fails** — Mitigation 2. Source contribution skipped, trace records `cross_fill_skipped: entity_match_failed`.
- **Stage 1 Haiku low confidence (<0.7)** — Mitigation 12. Auto-trigger Claude web search reconciliation. If reconciliation also fails, warning `low_confidence_resolution`, job continues.
- **Subsidiary detected, Canada checkbox not set** — Mitigation 8. Auto-enforce country filter, emit `subsidiary_geo_mismatch` warning surfaced as banner.
- **Cross-slide dedupe collision** — Mitigation 5. Accept the duplicate with `shared_role` badge on both slides.
- **Stage 3 final-fallback agent returns nothing** — slide marked "no contact found"; deck still ships with the placeholder.
- **Per-source circuit breaker open** — source skipped entirely; trace records the breaker state.
- **Logger flush failure** — log to stderr, continue. Never block on telemetry.
- **Live-progress write conflict** — silently drop (monotonic seq guard handles it).

### C. Caching & circuit breakers

- **Claude resolution cache.** TTL 30d. Key normalized: `(lowercase(strip_suffix(input_name)), primary_domain)` — Mitigation 9.
- **LinkedIn enrichment cache.** TTL 7d (LinkedIn data is time-sensitive). Key: `linkedin_url`.
- **Circuit breakers.** Per upstream API. 5 failures in 60s → open for 30s. State surfaced in trace.

### D. Frontend error surfaces

- **`current_stage == "failed"`** — error code + message + retry button + log tab open
- **`current_stage == "done"` with warnings** — banner listing warnings + degraded paths; deck still downloadable
- **Live-view connection loss** — backoff polling + "Reconnecting…" banner; re-sync from DB on reconnect

### E. Observability principle

The 7-level silent fallback chain that we're killing in `zoominfo_client.py` is the anti-pattern. **Every degraded path emits an `enrichment_trace` entry.** No silent failures. Devops can pull `debug_logs` from Supabase and reconstruct exactly what happened on any job.

---

## Testing Plan

### Framework
- Backend: pytest (existing)
- Frontend: Vitest (existing)
- Golden files for PPTX: `backend/tests/fixtures/golden_pptx/`
- Mock layer for upstream APIs: existing patterns in `conftest.py`

### Tests to DELETE

- All 14 Gamma test files (9 in `backend/`, 5 in `backend/tests/`)
- Any test asserting `slideshow_status` field
- Any test exercising `/api/generate-slideshow/{job_id}` retry endpoint
- ZI silent-fallback cascade tests in `test_zoominfo_client.py` covering the 7-level chain

### Tests to ADD

**1. Stage 1 (`test_bi_resolver_stage1.py`):**
- All 4 sources agree on canonical → no reconciliation fired
- Intra-service ambiguity → reconciliation fired
- Cross-service name divergence → reconciliation fired
- Haiku confidence <0.7 → reconciliation fired even without ambiguity (Mitigation 12)
- Cache hit on `(normalize(input), domain)` → no reconciliation call
- Cache key normalization: "Acme" and "ACME Inc" hit same entry (Mitigation 9)
- All 4 sources fail → `CompanyResolutionFailedError`

**2. Stage 3 (`test_bi_resolver_stage3.py`):** parametrized × 4 role buckets:
- ZI exact match returns complete contact → used as slide_contact
- ZI exact returns incomplete (no email) → cross-fill from Apollo → used
- ZI all tiers empty → Apollo cascade picks one → used
- All structured sources empty → fallback agent invoked → mock agent returns contact
- Fallback agent returns nothing → slide marked "no contact found"
- Short-circuit (Mitigation 1): ZI C-suite empty + ZI VP empty → skip ZI Director, jump to Apollo
- Systemic field absence (Mitigation 4): all candidates missing email → cascade short-circuits and accepts
- Same-person dedupe (Mitigation 5): cascade for CIO produces Alice; CTO cascade re-surfaces Alice → CTO cascade advances
- Cross-fill phantom rejection (Mitigation 2): Apollo's "John Smith" with different email than ZI's → cross-fill skipped
- Haiku no-citation rejection (Mitigation 3): LinkedIn response without `extracted_snippet` → treated as missing
- Canada checkbox: every cascade query includes `country=Canada`
- Subsidiary auto-enforce (Mitigation 8): subsidiary detected → cascade forced to subsidiary country

**3. Stage 4 (`test_llm_council_validator.py`):**
- Council receives only `slide_contacts[4]` + general intel, not full `contact_catalogue` (Mitigation 10)
- Validator output schema matches input shape (no formatting added)
- 20-specialist consensus still functions (port existing tests with formatting stripped)

**4. Stage 5 (`test_claude_formatter.py`):**
- Sonnet 4.6 mocked → output JSON matches slot manifest exactly
- Output references unknown slot → `FormatterOutputInvalidError`
- 3 consecutive malformed outputs → `FormatterOutputInvalidError`

**5. Stage 6 (`test_pptx_renderer.py`):** golden-file:
- Canned formatter output + test master template → generated `.pptx` structurally matches golden file
- Template missing from Supabase Storage → `MasterTemplateMissingError`
- Formatter outputs slot not in template → `SlotManifestDriftError` with mismatched slot name
- Required slot empty → `EmptyRequiredSlotError`
- Successful render → uploaded to Supabase Storage, public URL returned

**6. JobLogger (`test_job_logger.py`):**
- Structured entries buffered with `{ts, stage, step, level, msg, data}`
- Flush writes to `profile_requests.debug_logs` jsonb
- Flush failure → stderr log, job continues
- PII redactor masks `john@acme.com` → `j***@acme.com`
- `DEBUG_RAW_LOGS=true` disables redaction

**7. Live progress (`test_live_progress.py`):**
- Stage transition updates `current_stage`, `current_step`, `step_progress` columns
- `partial_results` accumulates monotonically
- Out-of-order stage update silently dropped (`WHERE current_stage_seq < new_stage_seq`)
- `/job-status/{id}` returns current state on each poll

**8. Frontend (`frontend/__tests__/...`):**
- `<RegionToggle />` posts `canada_only: true` when checked
- `<ConfidenceBadge />` maps score → High/Medium/Low with provisional thresholds
- Live view: 3 tabs render correct data, polls every 2s with backoff, redirects to detail on completion

**9. Integration / e2e (`test_pipeline_e2e.py`):**
- Happy path: profile request → all 6 stages → `.pptx` URL persisted → frontend downloads
- Failure path: master template missing → fail-loud → frontend shows error + retry
- Degraded path: GNews timeout → job completes with news empty, warning banner shown
- Cache path: same company twice in 30 days → second job hits cache, no Claude reconciliation
- Stage 3 fallback path: ZI/Apollo/PDL all empty → agent fires → returns contact → slide populated

### Tests to ADAPT

- `production_main` test suite — replace Gamma-specific assertions with PPTX assertions
- Job-status endpoint tests — replace `slideshow_status` polling assertions with synchronous completion
- Frontend job-detail page tests — adapt for new schema

### Coverage target

≥85% line coverage on new files. Mitigations 1–12 each have at least one explicit test.

---

## Red-Team Analysis & Mitigations

The data flow was reviewed from an "enemy agent" perspective during Session 2. The 12 distinct failure modes identified, and their mitigations, are baked into v3 (all except #7, which the user explicitly rejected in favor of hard cutover).

### Flaw 1: Cost blowup on no-such-role companies
**Impact:** HIGH
**Scenario:** A 50-person startup with no CIO walks the full cascade — ZI 4 tiers (empty), Apollo 4 tiers (empty), PDL 4 tiers (empty), Haiku web search (empty), then "any employee" fallback. 13+ API calls × 4 buckets = 52 calls/job worst case.
**Mitigation:** Short-circuit. If ZI returns 0 candidates in BOTH tier 1 (C-suite) AND tier 4 (VP), skip directly to Apollo. Signal: this company simply does not have this role at the senior level. Saves the wasted Director-tier and adjacent-title queries.

### Flaw 2: Cross-fill phantom data
**Impact:** HIGH
**Scenario:** ZI says "John Smith, CTO at Acme, email john@acme.com." Apollo cross-fills phone +1-555-1234 from a different "John Smith" (common name) at a different Acme. Pipeline silently merges incompatible records.
**Mitigation:** Cross-fill requires strong entity match. The source's contact record must match the ZI record on **email OR LinkedIn URL** — name-only is rejected. If neither match field is available, no cross-fill from that source for this candidate.

### Flaw 3: Haiku LinkedIn hallucination
**Impact:** HIGH
**Scenario:** LinkedIn pages are often JS-blocked / robots-blocked / partially loaded. Haiku 4.5 may fabricate a `start_date` if it cannot actually read the page but doesn't admit it.
**Mitigation:** Required output schema includes `extracted_snippet` and `source_url`. Responses without `extracted_snippet` are rejected and the field treated as missing. The snippet provides an auditable trail.

### Flaw 4: Infinite cascade on systemic field absence
**Impact:** HIGH
**Scenario:** Acme uses obfuscated emails on all their LinkedIn / company pages. Every candidate fails `is_complete` because email is never findable. Cascade walks all candidates, exhausts, falls back to "best of incomplete," but ships with missing email anyway. Wasted budget.
**Mitigation:** Track WHICH field is missing across candidates. If the same required field is missing for ALL examined candidates → treat as a company-level issue, accept incompleteness for that field globally, short-circuit the cascade. Emit `systemic_field_absence: <field>` warning.

### Flaw 5: Same person across multiple slides
**Impact:** HIGH
**Scenario:** Small company; the CEO is the de-facto CTO AND CIO. Cascade for CTO surfaces Alice; cascade for CIO ALSO surfaces Alice. Two slides show the same person without acknowledgment.
**Mitigation:** Cross-slide dedupe. Track `already_used_linkedin_urls`. If a candidate is already on another slide, advance to the next in this slide's cascade. If cascade exhausts with only duplicates, accept the duplicate but flag both slides with a `shared_role` badge in the slide footer.

### Flaw 6: Master template / slot manifest drift
**Impact:** HIGH
**Scenario:** User swaps the master `.pptx` (adds a new slide, renames placeholders). If we maintained a separate JSON slot manifest, it's now stale — formatter outputs reference slots that don't exist or misses new ones. Renderer fails or fills wrong slots.
**Mitigation:** Slot manifest is introspected dynamically from the master `.pptx` at render-time via python-pptx, not maintained as a separate file. Formatter prompt is built fresh from the introspected manifest each run. Renderer validates formatter output against manifest before fill; mismatch is fail-loud with the specific slot name.

### Flaw 7: Hard cutover with no rollback path
**Impact:** HIGH
**Status:** **MITIGATION REJECTED BY USER.** Hard cutover stays.
**Scenario:** WIP locked "delete Gamma in same PR." If PPTX breaks in prod, recovery = revert + redeploy (minutes, not seconds).
**Mitigation considered (rejected):** Feature flag for 1-2 weeks. Keep `gamma_slideshow.py` + `GAMMA_API_KEY` behind `RENDERER=pptx|gamma` env flag; delete in follow-up PR after PPTX is proven stable.
**User's stated reasoning for rejection:** Clean cutover preferred. Test suite + Render's quick revert path is acceptable safety net.

### Flaw 8: Subsidiary + no Canada checkbox = empty contacts
**Impact:** MEDIUM
**Scenario:** User enters "Acme Canada" without checking the region filter. Stage 1 resolves to subsidiary entity. Stage 3 cascade is global → returns 0 because subsidiary entity is small.
**Mitigation:** When Stage 1 resolves to a subsidiary (`is_subsidiary == true`) AND `canada_only == false`, auto-enforce `country = hq_country` of the subsidiary for Stage 3. Surface a banner on the dashboard: "We detected this is a Canadian subsidiary and filtered contacts accordingly."

### Flaw 9: Cache key too narrow
**Impact:** MEDIUM
**Scenario:** User enters "Acme" today, "ACME Inc" tomorrow. Cache misses despite same company.
**Mitigation:** Normalize input before keying. `cache_key = (lowercase(strip_suffix(input_name)), primary_domain)`. Suffix list includes Inc, LLC, Corp, Ltd, Pte, GmbH, plus localized variants.

### Flaw 10: LLM Council prompt explosion
**Impact:** MEDIUM
**Scenario:** If Council receives the full `contact_catalogue` (potentially 20+ contacts across 4 buckets × 5 candidates), prompt size balloons; cost rises and quality drops.
**Mitigation:** Council receives only the 4 `slide_contacts` + general intel. The full `contact_catalogue` goes straight to dashboard, bypassing Council.

### Flaw 11: GNews flakiness drags Stage 2
**Impact:** LOW
**Scenario:** GNews is fully wired but slowest leg of Stage 2 parallel calls determines stage latency. A 30-second GNews hang would block the job.
**Mitigation:** Hard 5s timeout on GNews. On timeout, news is empty, trace records `gnews: timed_out`, rest of intel proceeds.

### Flaw 12: Haiku Stage 1 single point of failure
**Impact:** LOW
**Scenario:** If Haiku 4.5 picks the wrong canonical company with no ambiguity signal, no reconciliation fires. Downstream stages run on the wrong entity.
**Mitigation:** Haiku output schema includes `confidence` (0–1). If confidence < 0.7 → trigger Claude web search reconciliation even without intra/cross-service ambiguity. Provides a second-opinion safety net for low-confidence picks.

### Mitigation summary

| # | Flaw | Mitigation | In v3? |
|---|------|-----------|--------|
| 1 | Cost blowup | C-suite + VP empty → skip to Apollo | ✅ |
| 2 | Cross-fill phantoms | Email/LinkedIn entity match required | ✅ |
| 3 | Haiku hallucination | Required citation in response schema | ✅ |
| 4 | Infinite cascade | Systemic field absence detection | ✅ |
| 5 | Same person dupes | Cross-slide LinkedIn dedupe | ✅ |
| 6 | Manifest drift | Dynamic introspection at render-time | ✅ |
| 7 | No rollback | Feature-flag rollback path | ❌ (rejected, hard cutover stays) |
| 8 | Subsidiary geo | Auto-enforce country on subsidiary detect | ✅ |
| 9 | Cache narrowness | Normalized cache key | ✅ |
| 10 | Council explosion | Council receives slide_contacts[4] only | ✅ |
| 11 | GNews drag | 5s hard timeout | ✅ |
| 12 | Haiku confidence | Reconciliation on confidence < 0.7 | ✅ |

---

## Trade-offs & Alternatives Evaluated

This section captures every alternative considered during the two brainstorm sessions, with the reasoning behind why each was accepted or rejected.

### Approach A vs B vs C (Session 1)

Three approaches were proposed for the overall architecture:

**Approach A — "Three Boxes" (selected, then refined in Session 2 to "five-stage v3")**

```
[BI Resolver] → [LLM Council validator] → [Claude formatting pass] → [PPTX renderer]
```

- ✅ Cleanest boundaries, easiest to test (each unit has a single interface)
- ✅ Three independent units = more files but more focused ones
- ✅ Directly addresses every gap from exploration
- ✅ Aligns with "skill" pattern: Claude authors copy, template enforces structure
- ❌ Highest LLM cost — multiple serial calls. Mitigated by Claude resolution caching.
- ❌ Largest PR / blast radius. Mitigated by thorough test suite.

**Approach B — "Two Boxes" (rejected)**

Fuse BI resolver and validator into one expanded LLM Council. Fuse the formatting pass into the renderer.

- ✅ Fewer moving parts, fewer LLM calls
- ❌ LLM Council prompt gets even bigger and harder to evolve
- ❌ Renderer mixes copywriting with mechanical filling — same concern-leakage that caused v3 brittleness
- ❌ Doesn't deliver the clean validator/formatter split the user explicitly asked for

**Approach C — "Minimal Surgical" (rejected)**

Keep `intelligence_gatherer.py` mostly intact. Surgical fixes only: ZoomInfo company-resolution, conflict-only Claude web search, `data_quality_score`, swap `gamma_slideshow.py` for `pptx_renderer.py`.

- ✅ Lowest risk, smallest PR
- ❌ User explicitly asked for full consolidation — minimal doesn't deliver
- ❌ Leaves silent fallback chains and 7-level ZoomInfo cascade intact
- ❌ Same ZI bandaids stick around

**Result:** Approach A confirmed in Session 2 with a substantial refinement to the BI Resolver itself (see "Surgical-contact pivot" below).

### Surgical-contact pivot (Session 2)

The original Approach A had a BI Resolver with company-wide source cascade (ZI → Apollo → PDL → Hunter → web search), each source pulling many contacts then sorting by completeness. User rejected this pattern in Session 2 in favor of per-role surgical pipeline:

> "this is a bit of a different shift from our approach right now which is going scorched earth and just spamming a bunch of contacts, instead we want to be a bit more surgical with our approach to finding contacts; we can still have more than 4 contacts in the dashboard but instead we will organize them by cto, coo, cfo and cio buckets and then our top contact should be the one which matches the closest by position and then we should do all we can to find their data instead of just picking the one that has the most complete data entree"

The pivot:

- **From:** company-wide source cascade, then bucket-sort the pool, then pick most-complete record per bucket
- **To:** per-role cascade within each source, pick most-proximate candidate, exhaustively enrich that candidate, advance only if not completable

This produces decks where the slide CTO actually has a CTO-like title (or a documented adjacent one), not just "the engineer at this company with the most complete data."

### Adjacency rule (Session 2 Q1)

Options:

- **Curated canonical lists** — explicit per-bucket title lists in code
- **LLM-judged adjacency** — Claude judges every candidate
- **Hybrid (selected)** — canonical lists handle common case fast; LLM fallback handles novel titles
- **Title-similarity string match** — brittle on synonyms like "Head of Engineering"

**Hybrid won** because it preserves auditability + speed for the 95% case while gracefully handling unusual titles at smaller / non-tech companies.

### Source roles in contact pipeline (Session 2 Q2)

Options:

- **Discovery + cross-fill, ZI-first (selected)** — ZI runs the full cascade; if zero, Apollo runs same cascade, then PDL; cross-fill from any source on missing fields
- **Cross-fill only** — ZI is the sole discoverer; Apollo/PDL/Hunter only fill missing fields
- **Discovery in parallel, ZI as tiebreaker** — all four discover in parallel, merge pool, dedupe

**Discovery + cross-fill ZI-first won** because it most closely mirrors the user's manual workflow and balances thoroughness against cost.

### Claude web search frequency (Session 2 Q3)

Options:

- **Always per slide contact (selected, with Haiku 4.5)** — every selected slide contact gets a Haiku LinkedIn search; 4 web searches/job baseline
- **Only when required fields missing** — cheaper, fewer validations
- **Always for discovery, conditional for enrichment** — hybrid

**Always-on with Haiku 4.5 won** because Haiku is cheap enough ($0.01–$0.02 per LinkedIn search) and the manual workflow ALWAYS includes the LinkedIn lookup step, so we match user expectation.

### Region filter shape (Session 2 Q5)

Options:

- **Region dropdown, scopes everything** — most future-proof but applies to general intel too
- **Region dropdown, contacts only** — dropdown UI, contacts-only scope
- **Canada-only checkbox, contacts only (selected)** — simplest UI, narrowest scope
- **Canada-only checkbox, scopes everything**

**Canada-only checkbox, contacts only won** because:
- The user's stated problem is contacts (multinational employees mixed in), not news
- Global company news is still relevant context regardless of which region's contacts are slide-promoted
- Single-checkbox UI is simpler than a dropdown; if expanded to other regions later, the UI swap is easy

### Agentic vs procedural (Session 2)

A significant architectural fork. User asked: "is it ever the play to package each stage of the pipeline as an AI agent with each step as a tool and also a rulebook on how to handle all these potential errors?"

Three approaches evaluated:

**Procedural (today's plan baseline)** — $0.10–$0.30/job, deterministic, testable, fast, brittle on unforeseen edge cases

**Full-agentic (each stage is a Claude agent with tools + rulebook)** — $1.50–$4.00/job, handles unforeseen edge cases, non-deterministic, harder to debug, 10–30× cost

**Hybrid: procedural hot path + targeted agentic escalation (selected)** — $0.15–$0.50/job. Common path stays cheap; agentic only fires when procedural cascade fully exhausts.

Specific agentic escalation points considered:

| Stage | Escalation candidate? | Decision |
|-------|----------------------|----------|
| Stage 1 reconciliation | Already agentic on conflict (Claude web search) | Keep |
| Stage 3 final fallback | "Any employee" tier → agentic Claude with tools | **Adopted in v3** |
| Stage 3 cross-source name reconciliation | Could escalate on ambiguity | Skip — rule-based match is enough |
| Stage 4 Council | Already 20-specialist consensus (kinda agentic) | Keep |
| Stage 5 formatter | Could loop with validate_slide_copy tool | Skip for v3, revisit if Sonnet output quality is poor |
| Stage 6 renderer | Pure mechanical | No escalation needed |

**Hybrid won** because:
- 95% of jobs hit a deterministic path that benefits from cost + speed
- The 5% that hit a wall get agentic resilience without the per-job cost overhead
- Net cost: ~$0.02–$0.04/job avg added by Stage 3 fallback agent firing on ~5–10% of jobs

### Hard cutover vs feature-flag rollback (Session 2 Q on Flaw 7)

Options:

- **Keep hard cutover (selected by user)** — delete Gamma in same PR
- **Feature flag for 1-2 weeks** — keep gamma_slideshow.py behind `RENDERER` env flag, delete in follow-up
- **Permanent dual-renderer support** — long-term dual-path maintenance

**Hard cutover stays.** User accepted the trade-off: clean codebase + revert-based recovery over instant-rollback safety net.

### Logging / live dashboard scope (Session 2)

Options:

- **All HIGH mitigations + logging + dashboard in v3 (selected)** — one PR, one launch
- **HIGH mitigations + logging in v3; dashboard as v3.1** — reduced frontend risk
- **HIGH mitigations only; logging + dashboard as v3.1** — tightest core scope

**Everything in v3** because the user wants operational visibility from day one of the new pipeline.

### Stakeholder slide count

Options:

- **Fixed 4 slides (CTO/CFO/CIO/COO), always populated (selected)** — Session 1 decision, confirmed Session 2
- **Variable 1-4 slides depending on data availability** — today's behavior
- **Up to 4 from canonical picker** — Session 1 mid-state, refined to "fixed 4 with fallback ladder"

**Fixed 4 won** for visual consistency. Worst-case fallback ladder ("any employee" → "no contact found") ensures the slide is always present even if data is poor.

### Required-field completeness criterion (Session 2)

User stated: "the only value that can be missing is a phone number sometimes if anything else is missing (which it shouldnt) we will also need to move onto the next contact."

So required = `{name, title, email, linkedinUrl, start_date}`. Phone optional.

### Master `.pptx` template hosting

Options:

- **Supabase Storage with public URL (selected)** — Session 1 decision
- **Bundled in worker Docker image** — would require redeploy to update
- **Self-hosted file server** — adds infra

**Supabase Storage won** for ease of updating + consistency with the rest of the data stack.

---

## Migration / Cutover Plan

### Sequencing

The implementation plan (to be written next) will sequence these milestones:

1. **Milestone 1 — New file scaffolding.** Create `bi_resolver.py`, `claude_formatter.py`, `pptx_renderer.py`, `job_logger.py`, `stage3_fallback_agent.py`, `circuit_breaker.py`. Stub interfaces. No removal of old files yet.
2. **Milestone 2 — Stage 1 implementation + tests.** Company resolution end-to-end with caching, reconciliation, mitigation tests.
3. **Milestone 3 — Stage 2 implementation + tests.** General intelligence with GNews wired + timeout.
4. **Milestone 4 — Stage 3 implementation + tests.** Per-role cascade, cross-fill, Haiku LinkedIn enrichment, completeness logic, fallback agent.
5. **Milestone 5 — Stage 4 refactor + tests.** Council prompts stripped of formatting concerns.
6. **Milestone 6 — Stage 5 + Stage 6 + tests.** Formatter + PPTX renderer + Supabase Storage upload + golden-file tests.
7. **Milestone 7 — Logger + live progress + frontend.** All cross-cutting infrastructure.
8. **Milestone 8 — Gamma removal.** Delete all Gamma files, env vars, frontend references in one commit.
9. **Milestone 9 — Integration tests + e2e.** Happy path, failure paths, degraded paths.
10. **Milestone 10 — Production cutover.** Deploy to Render. Master `.pptx` template uploaded to Supabase Storage. Run smoke tests on 5 known companies.

### Cutover deployment steps

1. Confirm master `.pptx` template is present in Supabase Storage bucket
2. Verify all new env vars are configured in Render
3. Deploy backend to Render
4. Deploy frontend to Vercel
5. Verify `/api/health` returns OK
6. Run 3 smoke-test jobs against known companies (Microsoft, a known mid-market account, a known small-co)
7. Inspect output decks for visual correctness
8. Monitor `data_quality_score` distribution for the first 24 hours
9. If any smoke test fails: revert deploys, re-investigate

### Rollback

Per the rejected Flaw 7 mitigation: rollback is "git revert + redeploy." Estimated time-to-rollback: 5-10 minutes assuming no DB schema migrations need to be reversed.

### Database migrations

`profile_requests` table:
- ADD columns: `debug_logs`, `current_stage`, `current_step`, `current_stage_seq`, `step_progress`, `partial_results`, `contact_catalogue`, `enrichment_trace`, `data_quality_score`
- DROP column: `slideshow_status` (only after frontend cutover is confirmed)

New tables:
- `claude_resolution_cache`
- `linkedin_enrichment_cache`

All migrations are additive except the `slideshow_status` drop, which is run AFTER frontend deploy lands.

---

## Open Items

### Pending user actions

- **Master `.pptx` template hand-off.** User has not yet provided the template file. Implementation of `pptx_renderer.py` depends on having this file to introspect for the slot manifest. Will block Milestone 6.

### Pending tuning decisions

- **`data_quality_score` thresholds.** Provisional cutoffs are High ≥ 0.75, Medium 0.4–0.75, Low < 0.4. Will be calibrated against the first week of production runs.
- **Stage 3 fallback agent turn cap.** Provisional cap is 5 tool calls; may need to raise to 8 if 5 proves too restrictive on truly obscure companies.
- **Haiku confidence threshold for Stage 1 reconciliation.** Provisional 0.7; may adjust based on observed false-negative rate.
- **Polling cadence for live view.** Provisional 2s; may switch to 1s for the active stage and 5s for completed stages to reduce DB load.

### Pending design questions that surfaced during brainstorm but were deemed scope-OK to defer

- **Region filter generalization (UK, AU, etc.).** Locked as Canada-only for v3. Future enhancement: dropdown.
- **Agentic Stage 5 formatter loop.** Skipped for v3; revisit if Sonnet output quality is poor in production.
- **Slideshow re-render endpoint.** Today's `/api/generate-slideshow/{job_id}` is being deleted. Future enhancement: a clean re-render endpoint that does not re-run BI Resolver (just Stages 5–6 from cached `validated_facts`).
- **GNews-driven rebrand detection.** Originally specced as a Session 1 idea ("search for `<company> renamed`, `acquired`, etc."). Now subsumed by Stage 1 Claude web search reconciliation; GNews stays an always-on parallel intel feed only.

---

## Locked Decisions Reference

Decisions that should not be revisited without explicit user override:

### From Session 1

1. PPTX skill pattern + user-provided `.pptx` master template (not Google Slides, not Gamma v4)
2. Fixed N slides mirroring current Gamma deck (4 stakeholder slides max)
3. Supabase Storage with public URL for hosted decks
4. Hard cutover — Gamma deleted in same PR
5. Full BI consolidation with rebrand + small-co as focal points
6. Claude web search only on genuine ambiguity (post candidate disambiguation)
7. Cascade for small companies: ZI → Apollo → PDL → Hunter → Claude web search
8. Approach 2 boundary: LLM Council = validator only, Claude = formatter, python-pptx = renderer

### From Session 2

9. Surgical per-role contact pipeline (not company-wide source cascade)
10. Per-role cascade: ZI C-suite exact → adjacent (hybrid canonical+LLM) → VP → Director, then Apollo, then PDL, then Stage 3 fallback agent
11. Required-fields completeness: `{name, title, email, linkedinUrl, start_date}`; phone optional
12. Hybrid adjacency rule (canonical lists + LLM fallback)
13. Cross-fill requires email or LinkedIn entity match (no name-only)
14. Haiku 4.5 always-on for LinkedIn enrichment (4 per job baseline)
15. Required citation (extracted_snippet + source_url) in Haiku output
16. Canada-only checkbox, contacts-only filter
17. Hybrid agentic pattern: procedural hot path + agentic Stage 3 final fallback
18. Hard cutover stays (Flaw 7 mitigation rejected)
19. All HIGH-impact mitigations + logging + live dashboard in v3 (not v3.1)
20. Sonnet 4.6 for formatter; Haiku 4.5 for resolver + LinkedIn enrichment
21. Slot manifest introspected dynamically (not maintained as separate JSON)
22. Council receives slide_contacts[4], not full catalogue
23. Polling-based live progress (not SSE)

---

## Appendix A — Prior Session Clarifying Q&A

The 8 clarifying questions and answers from Session 1 (2026-05-26):

| # | Question | Answer |
|---|----------|--------|
| 1 | PPTX format approach | Anthropic pptx skill **+** user-provided `.pptx` master template (mix of HTML-skill pattern and python-pptx mechanical fill) |
| 2 | Slide structure (fixed vs dynamic) | Fixed N slides, exactly mirror current Gamma deck (incl. up to 4 stakeholder profile slides via canonical picker — refined Session 2 to fixed 4) |
| 3 | Where the .pptx lives | Supabase Storage with public URL |
| 4 | Migration strategy | Hard cutover |
| 5 | BI scope | Full consolidation with rebrand + small-co as focal points |
| 6 | Rebrand detection mechanism | Preliminary ZoomInfo company-search/match → disambiguate by domain/industry/geo/headcount → Claude web search reconciliation only when ambiguous |
| 7 | Small-company strategy | Cascade ZI → Apollo → PDL → Hunter → Claude web search (refined Session 2 to per-role cascade) |
| 8 | Authoring boundary | LLM Council = validator only, Claude formatting pass = slide copy authoring, python-pptx = mechanical fill |

---

## Appendix B — This Session Clarifying Q&A

Session 2 (2026-05-27) verbatim user inputs and decisions:

**On the original Approach A confirmation:**

> "lets go into more in depth about this: there are a couple of elements i want to highlight as the end result of this new pipeline: namely most of the stuff will basically stay the same including the templates + resource recommendation and general business intelligence, what will change however is the contact pulling and enriching because that has been the most inconsistent part of this to date - going forward on the final slideshow output there will always be 4 contacts: a CTO, CFO, CIO and COO or adjacent executive position along with a complete catalogue of their information, start date, position, email, phone, linkedin, etc. (as we've outlined in the existing pipeline) there should always be a contact listed for each of these 4 slides..."

> "...heres the manual workflow that has been very effective in finding a complete suite of information regarding a contact: 1) determining which contact is suitable for the slide, on zoominfo under the company check the contacts under the c-suite filter, looking for a contact with a similar title, if not check vp filter, director, etc. 2) clicking on their contact in zoominfo i get most of the general information, position, email, phone, linkedin 3) i google their linkedin and there i get more auxiliary information like their start date and usually their profiles exist if they are high standing enough..."

> "heres how the entire flow should look a) user enters a company b) search it up on zoominfo, apollo, pdl, hunter and find the closest (if not exactly) matching company c) run the general intelligence pipeline which encompasses all the general knowledge leading up to the contacts section d) run the more comprehensive contact pipeline e) create the output for slides"

**On empty-role policy:**

> "the flow for this should be if there is absolutely no contact available you need to find someone, any person can do even if they are just an employee but we need to have 4 contacts. worst case worst case you just say no contact found and call it. i also want to flag that despite prioritizing a more surgical match-based approach we still value and place information completeness as a critical priority, the only value that can be missing is a phone number sometimes if anything else is missing (which it shouldnt) we will also need to move onto the next contact but the key different in approach is that we should procedurally move through contacts based on corporate proximity instead of pulling a bunch of contact queries at once and then sorting based on information completeness. if all contacts are missing key information then we can just use the one thats closest in position but i guess like its kind of like dual hierarchy in terms of prioritization based on the logic i outlined above"

**On adjacency rule (Q1):**
- Decision: Hybrid (canonical first, LLM fallback)

**On source roles (Q2):**
- Decision: Discovery + cross-fill, ZI-first

**On web search frequency (Q3):**
> "yeah do 1 but use a cheaper model like haiku / sonnet to validate this"
- Decision: Always-on per slide contact, Haiku 4.5

**On approach lock-in (Q4):**
- Decision: Lock approach + add Stage 1 refinement
> "1 more thing for the very first part for company resolution have all 4 services pull in parallel and then get the llm resolver to confirm the final output based on all 4 pulls; the claude layer in step 1 is only for the case in which there are conflicting names in either a) there are multiple adjacent results shown in the same service (ie zoominfo doesnt show company a but shows company ab and company ac) the llm resolves which one to pick and also if there is a need to pick a company in the first place b) names across different services are different (company a is shown as company ab in zoominfo and company ac in apollo) claude here can validate the naming difference and resolve any uncertainty"

**On components (Q5):**
- Decision: Looks good + raise the multinational subsidiary problem
> "for regional branches of international companies; often times we query a company a canada but then that is included as a part of company a and all the canadian contacts are mixed in - how can we resolve this in our new pipeline architecture; im thinking we have a checkbox for canada only when the user inputs the query and then we just add a step 3.5 if they check that box to add an additional canada only filter thoughts? evaluate this and let me know what you think"

**On region filter shape (Q6):**
> "lets do 3. canada only checkbox scopes contact only because global company news is still relevant to that company and we want data lol; also keep in mind there may also be the case the company appears as a subsidiary in our data providers too thats why stage 1 the company resolver is particularly important because it allows us to cut through some of the noisiness in these data providers"
- Decision: Canada-only checkbox, contacts only

**On data flow (Q7):**
- Decision: Data flow looks right, evaluate red-team + add logging + live dashboard
> "can you evaluate this flow from like an enemy agent perspective to identify potential flaws + if they can effectively account for the edge cases identified and if there is room for improvement"
> "i also want to modify our backend and frontend so that this a complete v3 on the backend the only change is that i want to log all jobs not just the ones per seller so that all jobs are stored in supabase and include the debug logs in this as well so that devops is able to go in and diagnose a job if there an error without rerunning it locally on the frontend i want to create a more robust dashboard, specifically when a job is running i want the user to be able to click in and see the entire flow being run, what step the pipeline is on, what data has been pulled already and also the logs for debugging"

**On scope of mitigations + logging + dashboard (Q8):**
- Decision: All HIGH-impact mitigations + logging + live dashboard in v3

**On hard-cutover vs feature flag (Q9):**
- Decision: Keep hard cutover

**On error handling (Q10):**
- Decision: Looks right + raise agentic vs procedural question
> "we have a bunch of edge considerations and overall this pipeline is trying to account for a bunch of uncontrollable possibilities, is it ever the play to package each stage of the pipeline as an ai agent with each step as a tool and also a rulebook on how to handle all these potential errors; im evaluating this on 2 metrics here a) cost and b) effectiveness let me know what you think"

**On agentic vs procedural (Q11):**
- Decision: Hybrid — agentic only at Stage 3 final fallback

**On testing plan (Q12):**
- Decision: Looks good — write the spec in two versions (concise + full PRD)

---

## Glossary

- **BI** — Business Intelligence; in this codebase refers to the data-gathering pipeline (firmographics, contacts, signals, opportunities, news) that precedes slide generation
- **Cascade** — Ordered fallback sequence within Stage 3 contact discovery
- **Canonical adjacency** — Pre-curated title list per role bucket (e.g., CTO ≈ Chief Engineering Officer)
- **Corporate proximity** — User's term for the rank ordering of candidates by title-match × seniority-tier
- **Cross-fill** — Filling missing fields on a candidate's record using data from a different source
- **Cross-slide dedupe** — Preventing the same person from appearing on multiple stakeholder slides
- **Enrichment trace** — Chronological log of every cascade step / source / outcome during a job's contact pipeline
- **Master `.pptx` template** — User-controlled PowerPoint file in Supabase Storage that defines slide structure + named placeholders
- **PII redaction** — Email/phone masking applied to log entries before they persist to Supabase
- **Procedural hot path** — Deterministic, code-driven cascade logic (vs Claude agent orchestration)
- **Region filter** — `canada_only` checkbox state, applied at Stage 3 cascade queries only
- **Role bucket** — One of CTO / CFO / CIO / COO
- **Slot manifest** — Map of placeholder names to slot metadata, introspected from the master `.pptx` at render-time
- **Stage 3 fallback agent** — Claude (Haiku 4.5) agent with tools, fires when procedural cascade exhausts
- **Systemic field absence** — Same required field missing across ALL examined candidates for a role bucket; treated as a company-level issue
- **Data quality score** — Weighted 0.0–1.0 score combining source reliability, cascade efficiency, field coverage, cross-source agreement

---

*End of design document.*
