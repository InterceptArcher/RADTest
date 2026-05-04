# Gamma Slideshow Template v3 — Structural & Content Refinements

**Date:** 2026-05-04
**Status:** Approved — ready for implementation plan
**Scope:** `backend/worker/gamma_slideshow.py`, `backend/llm_council.py`, plus a new test file

---

## Background

The current Gamma slideshow output (default template `g_76n9u56280zyiyz`, set 2026-03-20 in commit `1a761bf`) needs a structural refresh. The user has prepared a new Gamma template (`g_uost7x0lutmwtwd`) that introduces several visual refinements and new bracket-placeholder slots, and has identified two content-shape changes the code needs to make to feed the new template correctly:

1. Stakeholder map should be capped at exactly 4 canonical C-suite roles.
2. Recommended-solutions LLM output should be reliably broad (capability categories) rather than niche HP SKUs.

The current code path produces variable-length stakeholder sections (1 contact per `csuiteCategory` plus an unbounded list of `otherContacts`), and while the LLM prompt for `recommended_solution_areas` already constrains away from SKUs in slot #1, slots #2 and #3 lack that constraint, leaving room for drift.

This spec captures all 9 changes required to bring the deck output in line with the new template and the user's content-quality requirements.

---

## Goals

- Swap to template `g_uost7x0lutmwtwd` and feed it the new bracket placeholders correctly.
- Make stakeholder slide output deterministic and bounded: at most 4 slides — the best-fit contact for each of CTO, CFO, CIO, COO — emitted in that order, with a documented title-keyword fallback chain and a skip-when-no-plausible-match rule (so output is always real data, never a blank slot).
- Reinforce the existing LLM prompt so recommended-solutions outputs stay at the capability-category level (e.g., *"endpoint security posture"*) and never produce niche SKU titles (e.g., *"HP Wolf Pro Security Service"*).
- Preserve the HP-vendor framing throughout — the user wants HP positioned as the solution, just not at SKU-level granularity.

## Non-goals

- No changes to the HP-templated outreach assets (Email / LinkedIn / Call Script / Voicemail / Objection Handling) added 2026-03-20 in `1f49a0f`. Those stay HP-branded and verbatim.
- No changes to the LLM Council pipeline structure. We're editing one prompt's wording, not adding/removing fields or stages.
- No new `validated_data` fields. The data contract upstream is unchanged.
- No backend infrastructure changes (no new endpoints, no DB migrations, no Render config changes).

---

## Changes

### 1. Template ID swap

**File:** `backend/worker/gamma_slideshow.py:32, :46`

Change the default template ID:

```python
def __init__(self, gamma_api_key: str, template_id: str = "g_uost7x0lutmwtwd"):
    ...
    self.template_id = template_id or "g_uost7x0lutmwtwd"
```

Two occurrences. Anywhere the literal string `g_76n9u56280zyiyz` appears as the default, replace it.

### 2. Account type label — pass-through 4-bucket taxonomy

**File:** `backend/worker/gamma_slideshow.py` — replace the derivation around lines 1221-1229 and the formatter at line 277.

The new template's placeholder reads `[choose between (public/private/government/non-profit)]`. The user will update the template to allow all 4 strings.

Replace the current "map to Public Sector / Private Sector" logic with a 5→4 normalize:

```
LLM company_type input  →  emitted account_type
─────────────────────────────────────────────────
"Public"                →  "Public"
"Private"               →  "Private"
"Subsidiary"            →  "Private"        # held privately by parent
"Government"            →  "Government"
"Non-Profit"            →  "Non-Profit"
<anything else / empty> →  "Private"        # defensive default
```

Implement as a small pure function `_normalize_account_type(company_type: str) -> str` (case-insensitive substring matching, since LLM output occasionally pluralizes or adds qualifiers like "Publicly traded").

### 3. Pain points format

**File:** `backend/worker/gamma_slideshow.py` — pain-points emission block, both the `_format_for_template` path and the `_generate_markdown` path (currently around lines 819 and 1520).

The new template expects each pain point as a bolded title plus a separate analysis paragraph. Replace the current single-line bullet emission with:

```markdown
**{title}**

{description}
```

…repeated for the first 3 entries from `validated_data.pain_points` (or the existing fallback chain through `opportunity_themes_detailed.pain_points` and `opportunity_themes.pain_points`).

The data is already shaped as `{title, description}` — no LLM change needed.

### 4. Sales opportunities format

**File:** `backend/worker/gamma_slideshow.py` — opportunities emission block, both code paths (around lines 844 and 1568).

Per item, emit:

```markdown
**{n}. {title}**

{description}
```

…for the first 3 entries from `validated_data.sales_opportunities` (or fallback chain).

### 5. Stakeholder map — "Key Decision Makers at {company}" line

**File:** `backend/worker/gamma_slideshow.py` — the role-profile-alignment slide block.

Inject a literal line near the top of that slide:

```
Key Decision Makers at {company_name}
```

…where `company_name` comes from `validated_data.company_name` with the same fallback used elsewhere in the file (i.e., upstream `company_data["company_name"]`).

### 6. Stakeholder slide cap to 4 canonical roles

**File:** `backend/worker/gamma_slideshow.py` — replace the current "1 best per `csuiteCategory` + `otherContacts` + legacy fallback" stack (around lines 593-650) with a deterministic 4-role pipeline.

Extract a new private helper:

```python
def _pick_canonical_stakeholders(
    self,
    stakeholder_map: Dict[str, Any],
    fallback_profiles: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Returns up to 4 contacts, one each for CTO / CFO / CIO / COO in that
    order. Empty slots are skipped (so the result has 0-4 entries).

    Selection algorithm per role:
      1. Direct csuiteCategory match in stakeholder_map['stakeholders'].
      2. Title-keyword fallback against ALL contacts (executive +
         otherContacts + legacy stakeholder_profiles), ranked first by
         keyword match strength, then by seniority order:
              Chief > SVP > EVP > VP > Director > Manager > <other>
      3. De-duplicate against contacts already chosen for earlier roles
         (a contact can only fill one slot — if they match both CTO and
         CIO keywords, they take the earlier role).
      4. If nothing matches, the role is skipped — no blank slide.
    """
```

Title-keyword map (private constant in the module):

```
CTO  → ["technology", "engineering", "digital", "information systems",
        "innovation", "architect"]
CFO  → ["finance", "financial", "treasurer", "controller", "accounting"]
CIO  → ["information", "it ", "systems", "data", "infrastructure"]
COO  → ["operations", "operating", "field services", "service delivery"]
```

Note: spaces in keywords are intentional — `"it "` matches "Director of IT" but not "Director of Items". Match is case-insensitive substring against the contact's `title` field.

Output ordering is hard-coded **CTO → CFO → CIO → COO**. Skipped roles compress the list (no blank slot rendered).

`otherContacts` and the legacy `stakeholder_profiles` list become *fallback candidates only* — not their own slides.

### 7. Stakeholder profile slide structure

**File:** `backend/worker/gamma_slideshow.py` — per-stakeholder slide emission block.

For each of the 4 (or fewer) selected stakeholders:

**Under "Contact" subheading**, emit `name` and `title` on separate lines so the new template's `[name]` and `[title]` placeholders can address them independently:

```
Contact
**{name}**
{title}
```

**Under "Communication Preferences" subheading**, emit a filtered, ordered list. Order: Email → Phone → LinkedIn. Each channel renders only if its corresponding field on the contact is populated and non-empty:

```
Communication Preferences
- Email: {contact.email}        # only if email populated
- Phone: {contact.phone}        # only if phone populated
- LinkedIn: {contact.linkedin}  # only if linkedin populated
```

A contact with email + linkedin but no phone shows two bullets, not three. A contact with no populated channels shows the heading but no bullets — that case shouldn't occur in practice since the canonical-picker requires at least name+title, but the renderer is defensive.

The phone fallback chain established in commit `198d20a` (`top-level → contact dict → company_phone`) is preserved for populating the phone field before the filter runs.

### 8. Recommended solutions section — no code change

The LLM prompt at `backend/llm_council.py:504-508` already constrains slot #1's description to broad capability categories (*"NOT specific HP product lines or SKUs"*), and the code-side fallbacks in `gamma_slideshow.py:852-854` are already vendor-broad. The only weakness is that slots #2 and #3 inherit the constraint loosely — addressed in change 9 below.

### 9. Reinforce the `recommended_solution_areas` LLM prompt

**File:** `backend/llm_council.py:504-508`

Strengthen the existing prompt to reduce LLM drift toward SKU-level titles. Three edits:

(a) Repeat the no-SKU constraint in slots #2 and #3 (currently only slot #1 has it).

(b) Add concrete examples of acceptable vs. unacceptable titles inside slot #1's description:

```
✓ Acceptable: "endpoint security posture", "AI-ready workstation fleet",
              "managed device lifecycle", "hybrid-work device strategy"
✗ Unacceptable: "HP Wolf Pro Security Service", "HP Z by HP for AI",
                "HP EliteBook 840 G10", "HP Anyware"
```

(c) Tighten the directive: replace `"NOT specific HP product lines or SKUs"` with `"MUST NOT include specific HP product names, SKU codes, or model numbers"`.

This is purely emphasis — the schema (`{title, description}`) and the field name (`recommended_solution_areas`) are unchanged. No code changes outside this prompt block; no breaking change for any downstream consumer.

---

## Architecture

No new modules. No new classes. All edits live inside the existing `_format_for_template()` and `_generate_markdown()` paths in `gamma_slideshow.py`, plus the one prompt block in `llm_council.py`.

The `validated_data` contract upstream is unchanged. The Gamma API call shape is unchanged. The output URL extraction, polling, and reconcile paths added in commit `cfa67c5` (2026-05-04) are unchanged.

The one tactical extraction worth doing for clarity is the new `_pick_canonical_stakeholders()` helper. Today's logic for picking C-suite contacts is inlined and tangled with `otherContacts` merging and a legacy-fallback branch. Pulling the canonical picker out:

- Makes the test surface clean (the picker is pure data → data, easy to test with synthetic dicts).
- Removes the legacy fallback branch from the hot path (it only runs as one of the keyword-match candidate sources, not as a special code path).
- Lets the keyword-fallback rule live in one place rather than scattered.

`otherContacts` and the legacy list aren't deleted from the module — they remain as candidate sources inside the picker. Just no longer get their own slides.

## Data flow

```
LLM Council
   ↓ (validated_data dict — UNCHANGED shape)
production_main.process_company_profile
   ↓
GammaSlideshowCreator.create_slideshow
   ↓
_format_for_template(validated_data)            ← edits 2,3,4,5,6,7
_generate_markdown(validated_data)              ← edits 3,4 (mirror)
   ↓ (markdown / inputText)
_send_to_gamma(...)                              ← edit 1 (template ID flows through)
   ↓
Gamma API → polling → URL
```

Edit 9 lives upstream in the LLM Council, not in the slideshow code at all — its effect propagates naturally through `validated_data.recommended_solution_areas` into the existing solutions emission block.

## Testing

New file: `backend/tests/test_gamma_template_v3.py`

Following the same TDD pattern as `backend/tests/test_gamma_pending_recovery.py` (synthetic dicts, no real Gamma calls, the existing `FakeAsyncClient` infrastructure where applicable).

Test coverage:

**Template ID**
- `GammaSlideshowCreator()` defaults `template_id` to `"g_uost7x0lutmwtwd"`.

**Account type normalization**
- `Public` / `Private` / `Government` / `Non-Profit` pass through verbatim.
- `Subsidiary` → `Private`.
- Mixed-case input (e.g. `"public"`, `"PUBLIC"`, `"Publicly traded"`) normalizes correctly.
- Empty string / unknown bucket → `Private`.

**Pain points formatter**
- 3 pain points each emit `**title**` + blank line + description.
- 4th pain point in input is ignored (cap at 3).
- Reads through fallback chain: `pain_points` → `opportunity_themes_detailed.pain_points` → `opportunity_themes.pain_points`.

**Sales opportunities formatter**
- 3 opportunities emit numbered `**1. title**` / `**2. title**` / `**3. title**` plus blurbs.

**"Key Decision Makers at {company}" line**
- Renders with company_name interpolated.
- Falls back gracefully when `validated_data.company_name` is missing (uses `company_data["company_name"]`).

**`_pick_canonical_stakeholders` helper**
- Returns CTO/CFO/CIO/COO in that exact order when all 4 csuiteCategory matches exist.
- Returns empty list when stakeholder_map is empty and no fallback candidates exist.
- Falls back to title-keyword matching when csuiteCategory is missing (e.g., a contact with title "VP of Operations" fills the COO slot).
- Honors seniority ranking when multiple candidates match (Chief > SVP > VP > Director > Manager).
- De-duplicates: a contact who matches both CTO and CIO keywords takes the earlier slot only; the later slot then looks for its own next-best match.
- Skips a role gracefully when nothing in the contact pool matches (output has 3 contacts, not 4 with one blank).
- Reads `otherContacts` and legacy `stakeholder_profiles` as candidate sources but doesn't emit them as their own slides.

**Communication preferences filter**
- Contact with email + phone + linkedin → 3 bullets in `Email | Phone | LinkedIn` order.
- Contact with email + linkedin → 2 bullets (Phone omitted).
- Contact with phone only → 1 bullet.
- Contact with no channels → no bullets (heading only — defensive).

**Recommended-solutions prompt** (in `backend/llm_council.py`)
- Inspect the prompt-builder function output to assert all three slot descriptions contain a no-SKU constraint string (e.g. assert `"MUST NOT"` or the substring `"product names"` appears in each of the 3 slot descriptions).
- Snapshot test against an example marker so we can refactor the prompt without losing the constraint.

**Regression**
- Run the existing `test_gamma_pending_recovery.py` suite to confirm the polling / reconcile / lazy-reconcile behavior added 2026-05-04 still passes after these refactors.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| `_format_for_template` and `_generate_markdown` drift apart on pain-points / opportunities format | Both blocks updated in the same change; tests assert the markdown emitted by both paths matches the new format |
| Title-keyword fallback picks wrong person when titles overlap (e.g., "Chief Information Security Officer" pulled into CIO slot when the user actually wants CISO=skipped) | Keyword `"information"` is too broad alone; `"information systems"` is more discriminating. Risk acknowledged — tests cover the common edge cases (CISO, COO/Operations, CTO/Tech). Tune the keyword list if production runs surface mis-picks |
| Subsidiary → Private mapping is wrong for users who expect public-listed parent → Public | Documented in the design; user has flagged they're OK with this default. Easy to revisit by adding a `parent_company_type` lookup if needed |
| LLM still drifts toward SKU titles despite reinforced prompt | Tests assert prompt content, not LLM output. The prompt edit is best-effort emphasis — if drift continues, follow-up could add a post-LLM regex scrub or a validator pass. Out of scope for this change |
| `otherContacts` users who relied on those slides will see them disappear | Documented behavior change. Users who want non-C-suite contacts in the deck need to surface them through a different mechanism (out of scope) |

## Migration / rollout

- Single PR, single deploy. No feature flag needed — the template ID and the markdown format are coupled, and rolling out half this change would render misaligned decks.
- Render auto-deploys on push to `main`. The Vercel frontend is unaffected (no API contract change).
- The user must update the new template (`g_uost7x0lutmwtwd`) on Gamma's side to allow `Government` and `Non-Profit` in the account-type placeholder before the deploy. This is a Gamma-UI edit, not a code change.

## Out of scope (deliberately)

- Changes to HP outreach templates (Email / LinkedIn / Call Script / Voicemail / Objection Handling).
- Changes to the content audit asset matcher (still feeds into the recommended sales program slide).
- Changes to the LLM Council schema or pipeline stages.
- Changes to phone-number extraction logic.
- A "Retry slideshow" UI button (orthogonal to template work — could come later).
- Surfacing `slideshow_error` to the frontend (orthogonal — captured in memory file `project_slideshow_dual_failure.md`).

## Acceptance criteria

A regenerated BC Liquor deck against the new template should:

1. Use template `g_uost7x0lutmwtwd`.
2. Show "Government" in the executive snapshot account-type field (BC Liquor is a Crown corp).
3. Show exactly 3 pain points, each with bolded title and separate description paragraph.
4. Show exactly 3 sales opportunities, each numbered with bolded title and separate validation blurb.
5. Show "Key Decision Makers at BC Liquor Distribution Branch" on the role-profile-alignment slide.
6. Show at most 4 stakeholder profile slides — best-fit contacts for CTO / CFO / CIO / COO in that order. Skip any role with no plausible contact.
7. Each stakeholder slide shows name and title on separate lines, plus a Communication Preferences list filtered to populated channels (Email / Phone / LinkedIn priority).
8. Show recommended solution titles at capability-category granularity ("endpoint security posture") rather than SKU level ("HP Wolf Pro Security Service for SMB").

All acceptance items are verifiable by visual inspection of the generated deck.
