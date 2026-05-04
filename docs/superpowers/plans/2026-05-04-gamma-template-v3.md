# Gamma Template v3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring `backend/worker/gamma_slideshow.py` and the `recommended_solution_areas` LLM prompt into alignment with the new Gamma template `g_uost7x0lutmwtwd`, including a new 4-bucket account-type taxonomy, restructured pain-points / sales-opportunities formatting, deterministic 4-role canonical stakeholder selection (CTO/CFO/CIO/COO with CISO last-resort fallback for CIO), structured contact + filtered communication preferences per profile, and reinforced anti-SKU language.

**Architecture:** All changes live in two production files (`backend/worker/gamma_slideshow.py`, `backend/llm_council.py`) plus one new test file (`backend/tests/test_gamma_template_v3.py`). No new modules. The `validated_data` data contract upstream is unchanged. One private helper is extracted (`_pick_canonical_stakeholders`) to make the canonical-role selection algorithm testable in isolation.

**Tech Stack:** Python 3.10, FastAPI, pytest + pytest-asyncio (auto mode), httpx for the existing Gamma client. Test patterns follow `backend/tests/test_gamma_pending_recovery.py` (synthetic dicts, `FakeAsyncClient` only when network mocking is needed — most new tests are pure data-in / markdown-out).

---

## Reference

- **Spec:** `docs/superpowers/specs/2026-05-04-gamma-template-v3-design.md`
- **Existing patterns to follow:** `backend/tests/test_gamma_pending_recovery.py` for async fixtures and httpx mocking
- **Test framework convention:** Tests live under `backend/tests/`, run with `cd backend && python3 -m pytest tests/<file> -v`
- **Commit message convention:** Follow recent style — `feat:` / `fix:` / `refactor:` / `docs:` prefix; concise body; sign-off line `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `backend/worker/gamma_slideshow.py` | Modify | Template ID swap; account-type normalization helper; pain-points + opportunities markdown emission; slide-7 lock wording; canonical stakeholder picker; per-stakeholder slide rendering |
| `backend/llm_council.py` | Modify | Reinforce `recommended_solution_areas` prompt (no-SKU constraint repeated in all 3 slot descriptions, concrete examples, "MUST NOT" wording) |
| `backend/tests/test_gamma_template_v3.py` | Create | 11 task-aligned test cases covering every change |

`validated_data` upstream contract: unchanged. No backend route changes. No frontend changes. No DB or infra changes.

---

## Task 1: Template ID swap

**Files:**
- Modify: `backend/worker/gamma_slideshow.py:32` and `backend/worker/gamma_slideshow.py:46`
- Create / extend: `backend/tests/test_gamma_template_v3.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_gamma_template_v3.py` with this content:

```python
"""
TDD tests for Gamma Template v3 (template g_uost7x0lutmwtwd).

Spec: docs/superpowers/specs/2026-05-04-gamma-template-v3-design.md

Patterns mirror tests/test_gamma_pending_recovery.py — synthetic
validated_data dicts, no real Gamma calls. Helpers and pure markdown
emitters are tested directly; the network-touching paths reuse the
FakeAsyncClient fixture pattern.
"""
import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Task 1: Template ID swap
# ---------------------------------------------------------------------------

def test_default_template_id_is_v3():
    """
    The new default template ID is g_uost7x0lutmwtwd. Both the constructor
    default and the instance-attribute fallback must reflect this.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    assert creator.template_id == "g_uost7x0lutmwtwd", (
        f"expected default template g_uost7x0lutmwtwd, got {creator.template_id!r}"
    )


def test_explicit_template_id_overrides_default():
    """Caller-supplied template_id wins over the default — sanity check."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(
        gamma_api_key="test-key",
        template_id="g_some_other_id",
    )
    assert creator.template_id == "g_some_other_id"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py::test_default_template_id_is_v3 -v
```

Expected: FAIL with `AssertionError: expected default template g_uost7x0lutmwtwd, got 'g_76n9u56280zyiyz'`.

- [ ] **Step 3: Implement minimal change**

Edit `backend/worker/gamma_slideshow.py`. There are exactly two literal occurrences of `"g_76n9u56280zyiyz"` to update — both are defaults for the same attribute, near the top of `GammaSlideshowCreator`:

- Line 32 (constructor signature default):
  ```python
  def __init__(self, gamma_api_key: str, template_id: str = "g_uost7x0lutmwtwd"):
  ```
- Line 46 (instance fallback):
  ```python
  self.template_id = template_id or "g_uost7x0lutmwtwd"
  ```

Also update the inline docstring/comment at line 39 if it names the old ID:
  ```python
  # Default: g_uost7x0lutmwtwd (HP RAD Intelligence template v3)
  ```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/RADTest && git add backend/worker/gamma_slideshow.py backend/tests/test_gamma_template_v3.py
git commit -m "$(cat <<'EOF'
feat(gamma): swap default template to g_uost7x0lutmwtwd (v3)

First step of the v3 template rollout. Bumps the default template ID
in both constructor signature and instance-attribute fallback so all
new slideshows use the v3 layout.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Account type normalization helper

**Files:**
- Modify: `backend/worker/gamma_slideshow.py` — add `_normalize_account_type` near other module-level helpers; replace derivation around lines 1221-1229 and the formatter at line 277
- Modify: `backend/tests/test_gamma_template_v3.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_gamma_template_v3.py`:

```python
# ---------------------------------------------------------------------------
# Task 2: Account type normalization (5 → 4 bucket pass-through)
# ---------------------------------------------------------------------------

def test_normalize_account_type_passthrough_buckets():
    """Public, Private, Government, Non-Profit pass through verbatim."""
    from worker.gamma_slideshow import _normalize_account_type
    assert _normalize_account_type("Public") == "Public"
    assert _normalize_account_type("Private") == "Private"
    assert _normalize_account_type("Government") == "Government"
    assert _normalize_account_type("Non-Profit") == "Non-Profit"


def test_normalize_account_type_subsidiary_to_private():
    """Subsidiary collapses to Private — held privately by parent."""
    from worker.gamma_slideshow import _normalize_account_type
    assert _normalize_account_type("Subsidiary") == "Private"


def test_normalize_account_type_case_insensitive():
    """Accept lowercase and mixed-case variants from the LLM."""
    from worker.gamma_slideshow import _normalize_account_type
    assert _normalize_account_type("public") == "Public"
    assert _normalize_account_type("PUBLIC") == "Public"
    assert _normalize_account_type("Publicly traded") == "Public"
    assert _normalize_account_type("government agency") == "Government"
    assert _normalize_account_type("non-profit organization") == "Non-Profit"
    assert _normalize_account_type("nonprofit") == "Non-Profit"


def test_normalize_account_type_unknown_defaults_to_private():
    """Empty / unrecognized strings default to Private."""
    from worker.gamma_slideshow import _normalize_account_type
    assert _normalize_account_type("") == "Private"
    assert _normalize_account_type("???") == "Private"
    assert _normalize_account_type(None) == "Private"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v -k normalize_account_type
```

Expected: 4 FAIL with `ImportError: cannot import name '_normalize_account_type'`.

- [ ] **Step 3: Implement the helper and replace existing derivation**

In `backend/worker/gamma_slideshow.py`, near the top of the module (right after the existing imports and before the `GammaSlideshowCreator` class — module-level so it's importable for tests), add:

```python
def _normalize_account_type(company_type) -> str:
    """
    Map LLM-emitted company_type values into the 4-bucket account-type
    taxonomy used by Gamma template v3.

    LLM input (5 buckets): Public | Private | Subsidiary | Government | Non-Profit
    Output (4 buckets):    Public | Private | Government | Non-Profit

    Subsidiary collapses to Private (subsidiary is privately held by parent).
    Unknown / empty / None defaults to Private (defensive — most companies
    in our data set are private).

    Match is case-insensitive substring. "publicly traded" → Public,
    "government agency" → Government, "nonprofit" → Non-Profit, etc.
    """
    if not company_type or not isinstance(company_type, str):
        return "Private"
    s = company_type.strip().lower()
    # Order matters: check more specific terms before generic ones.
    if "non-profit" in s or "nonprofit" in s or "non profit" in s:
        return "Non-Profit"
    if "government" in s or s.startswith("gov"):
        return "Government"
    if "public" in s:
        return "Public"
    if "subsidiary" in s:
        return "Private"
    if "private" in s:
        return "Private"
    return "Private"
```

Then replace the existing derivation in the markdown emitter. Find the block currently at `gamma_slideshow.py:1221-1229`:

```python
account_type = validated_data.get('account_type', '')
if not account_type:
    company_type = validated_data.get('type', validated_data.get('company_type', ''))
    if 'government' in str(company_type).lower() or 'public' in str(company_type).lower():
        account_type = 'Public Sector'
    else:
        account_type = 'Private Sector'
markdown += f"**Account Type:** {account_type}\n\n"
```

Replace with:

```python
# v3 template: 4-bucket account-type taxonomy. Prefer LLM company_type
# over upstream account_type so we get the canonical Public/Private/
# Government/Non-Profit label.
account_type = _normalize_account_type(
    validated_data.get('company_type')
    or validated_data.get('type')
    or validated_data.get('account_type')
    or ""
)
markdown += f"**Account Type:** {account_type}\n\n"
```

And update the formatter at `gamma_slideshow.py:277` (the `=== EXECUTIVE SNAPSHOT ===` block). The current line:

```python
data += f"Account Type: {validated_data.get('account_type', validated_data.get('target_market', validated_data.get('company_type', 'Private Sector')))}\n"
```

Replace with:

```python
data += f"Account Type: {_normalize_account_type(validated_data.get('company_type') or validated_data.get('type') or validated_data.get('account_type') or '')}\n"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v
```

Expected: all 6 tests PASS (Task 1's 2 + Task 2's 4).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/RADTest && git add backend/worker/gamma_slideshow.py backend/tests/test_gamma_template_v3.py
git commit -m "$(cat <<'EOF'
feat(gamma): 4-bucket account-type taxonomy via _normalize_account_type

The new v3 template has a [choose between (public/private/government/
non-profit)] placeholder. _normalize_account_type collapses the LLM's
5 input buckets (Public, Private, Subsidiary, Government, Non-Profit)
into the template's 4 by routing Subsidiary → Private. Replaces the
old "Public Sector / Private Sector" string derivation at both the
template-format and markdown paths.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Pain points formatter

**Files:**
- Modify: `backend/worker/gamma_slideshow.py` — pain-points emission in `_format_for_template` (around line 470 — read the surrounding code to find the exact existing block) AND in the markdown path (around line 819 / 1520)
- Modify: `backend/tests/test_gamma_template_v3.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_gamma_template_v3.py`:

```python
# ---------------------------------------------------------------------------
# Task 3: Pain points format — bolded title + blank line + description
# ---------------------------------------------------------------------------

def _make_validated_with_pain_points():
    return {
        "company_name": "Acme Co",
        "domain": "acme.com",
        "validated_data": {"company_name": "Acme Co"},
        "pain_points": [
            {"title": "Aging device fleet",
             "description": "Most laptops are 4+ years old, hurting productivity."},
            {"title": "Inconsistent endpoint security",
             "description": "Mixed OS versions complicate patching and policy."},
            {"title": "Slow procurement cycle",
             "description": "Hardware refreshes take 90+ days vs industry 30."},
        ],
    }


def test_pain_points_format_template_path_emits_bold_title_blank_description():
    """
    The template-path formatter (_format_for_template) emits each pain point
    as **title** on its own line, then a blank line, then the description.
    Caps at 3 entries.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    company = _make_validated_with_pain_points()
    output = creator._format_for_template(company)

    assert "**Aging device fleet**" in output
    assert "Most laptops are 4+ years old, hurting productivity." in output
    assert "**Inconsistent endpoint security**" in output
    assert "Mixed OS versions complicate patching and policy." in output
    assert "**Slow procurement cycle**" in output

    # Each title must be followed by a blank line and then the description
    # (verify by checking the title and description appear in order with a
    # newline between them, not inline).
    idx_title_1 = output.index("**Aging device fleet**")
    idx_desc_1 = output.index("Most laptops are 4+ years old")
    between = output[idx_title_1:idx_desc_1]
    assert "\n\n" in between, (
        "expected blank line between title and description, got: " + repr(between)
    )


def test_pain_points_format_caps_at_three_entries():
    """Inputs of >3 entries truncate to 3."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    company = _make_validated_with_pain_points()
    company["pain_points"].append({"title": "Fourth", "description": "Should not render."})
    output = creator._format_for_template(company)
    assert "**Fourth**" not in output
    assert "Should not render." not in output


def test_pain_points_format_reads_fallback_chain():
    """
    If validated_data.pain_points is missing, the formatter falls through
    to opportunity_themes_detailed.pain_points, then opportunity_themes.pain_points.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    company = {
        "company_name": "Fallback Co",
        "validated_data": {"company_name": "Fallback Co"},
        "opportunity_themes_detailed": {
            "pain_points": [
                {"title": "Nested pain", "description": "From the detailed nest."},
            ],
        },
    }
    output = creator._format_for_template(company)
    assert "**Nested pain**" in output
    assert "From the detailed nest." in output
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v -k pain_points
```

Expected: 3 FAIL — current format is single-line bullets, not bold-title + paragraph.

- [ ] **Step 3: Implement the pain-points format change**

In `backend/worker/gamma_slideshow.py`, find the pain-points emission inside `_format_for_template` (roughly the block immediately above the opportunities block at line 487 — open the file and locate the `=== PAIN POINTS ===` or equivalent header). The existing emission likely looks like:

```python
if isinstance(p, dict):
    data += f"{i}. {p.get('title', p)}\n"
    if p.get('description'):
        data += f"   {p['description']}\n"
```

Replace with the v3 format (bold title, blank line, description, blank line, cap at 3, fallback chain):

```python
# v3 format: bolded title, blank line, description paragraph.
pain_points = (
    validated_data.get('pain_points')
    or validated_data.get('opportunity_themes_detailed', {}).get('pain_points')
    or validated_data.get('opportunity_themes', {}).get('pain_points')
    or []
)
if pain_points:
    data += "=== PAIN POINTS ===\n\n"
    for p in pain_points[:3]:
        if isinstance(p, dict):
            title = p.get('title', '')
            desc = p.get('description', '')
            data += f"**{title}**\n\n{desc}\n\n"
        else:
            data += f"**{p}**\n\n"
```

Then locate the markdown-path equivalent (around `gamma_slideshow.py:819` and `:1520` — the file has two paths, find both via grep `pain_points = validated_data.get('pain_points')` and update both blocks to the same shape). The markdown path uses `markdown +=` instead of `data +=` and may have a different section header name; preserve the existing header but replace the per-item emission with the new bold-title + blank + description shape.

If the old code references `validated_data.pain_points` directly (not through `validated_data` being top-level vs. nested), be sure to use the same data accessor as the existing block.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v
```

Expected: all tests so far PASS (10 total: Task 1's 2 + Task 2's 4 + Task 3's 3 + 1 fallback test).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/RADTest && git add backend/worker/gamma_slideshow.py backend/tests/test_gamma_template_v3.py
git commit -m "$(cat <<'EOF'
feat(gamma): pain points emit bold title + blank + description for v3

The v3 template's pain-points slide expects each of the 3 pain points
as a bolded [title] on its own line, a line break, then an [Analysis
for #] paragraph. Updates both _format_for_template and the markdown
path. Caps at 3 entries; reads through the existing fallback chain.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Sales opportunities formatter

**Files:**
- Modify: `backend/worker/gamma_slideshow.py:487-497` (`_format_for_template` opportunities block) AND the markdown-path equivalent around line 844 / 1568
- Modify: `backend/tests/test_gamma_template_v3.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
# ---------------------------------------------------------------------------
# Task 4: Sales opportunities format — # bold title + blank line + blurb
# ---------------------------------------------------------------------------

def _make_validated_with_opportunities():
    return {
        "company_name": "Acme Co",
        "validated_data": {"company_name": "Acme Co"},
        "sales_opportunities": [
            {"title": "Endpoint refresh", "description": "Validate appetite for a fleet refresh aligned to FY26 capex."},
            {"title": "Hybrid work enablement", "description": "Confirm hybrid mandate and current device gaps."},
            {"title": "Security posture", "description": "Probe maturity of endpoint security tooling and policy."},
        ],
    }


def test_sales_opportunities_format_template_path():
    """
    Each opportunity emits as **N. title** on one line, blank, then blurb.
    Numbers are 1-indexed and visible in the bold span.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    company = _make_validated_with_opportunities()
    output = creator._format_for_template(company)

    assert "**1. Endpoint refresh**" in output
    assert "**2. Hybrid work enablement**" in output
    assert "**3. Security posture**" in output
    assert "Validate appetite for a fleet refresh aligned to FY26 capex." in output

    # Verify blank line between numbered title and blurb
    idx_title = output.index("**1. Endpoint refresh**")
    idx_blurb = output.index("Validate appetite for a fleet refresh")
    between = output[idx_title:idx_blurb]
    assert "\n\n" in between


def test_sales_opportunities_caps_at_three():
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    company = _make_validated_with_opportunities()
    company["sales_opportunities"].append(
        {"title": "Extra", "description": "Should not render."}
    )
    output = creator._format_for_template(company)
    assert "**4. Extra**" not in output
    assert "Should not render." not in output
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v -k sales_opportunities
```

Expected: 2 FAIL — current format is `1. Title\n   description\n`, no bold and no blank line.

- [ ] **Step 3: Implement the format change**

In `backend/worker/gamma_slideshow.py:487-497`, replace the existing opportunities block:

```python
opportunities = validated_data.get('sales_opportunities', [])
if opportunities:
    data += "=== SALES OPPORTUNITIES ===\n\n"
    for i, opp in enumerate(opportunities, 1):
        if isinstance(opp, dict):
            data += f"{i}. {opp.get('title', opp)}\n"
            if opp.get('description'):
                data += f"   {opp['description']}\n"
        else:
            data += f"{i}. {opp}\n"
        data += "\n"
```

…with:

```python
# v3 format: numbered + bolded title, blank line, validation blurb.
opportunities = (
    validated_data.get('sales_opportunities')
    or validated_data.get('opportunity_themes_detailed', {}).get('sales_opportunities')
    or validated_data.get('opportunities')
    or []
)
if opportunities:
    data += "=== SALES OPPORTUNITIES ===\n\n"
    for i, opp in enumerate(opportunities[:3], 1):
        if isinstance(opp, dict):
            title = opp.get('title', '')
            desc = opp.get('description', '')
            data += f"**{i}. {title}**\n\n{desc}\n\n"
        else:
            data += f"**{i}. {opp}**\n\n"
```

Then locate the markdown path at `gamma_slideshow.py:844` (and `:1568` — there may be two locations) and apply the same transformation.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v
```

Expected: all tests PASS (12 total).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/RADTest && git add backend/worker/gamma_slideshow.py backend/tests/test_gamma_template_v3.py
git commit -m "$(cat <<'EOF'
feat(gamma): sales opportunities emit numbered bold title + blurb for v3

The v3 template's sales opportunities slide expects each of the 3
opportunities as **N. title** on one line, a line break, then a
[validate blurb] paragraph. Updates both _format_for_template and
the markdown path. Caps at 3 entries; reads through the existing
fallback chain.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Slide-7 lock instruction refinement

**Files:**
- Modify: `backend/worker/gamma_slideshow.py:253` and `backend/worker/gamma_slideshow.py:648`
- Modify: `backend/tests/test_gamma_template_v3.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
# ---------------------------------------------------------------------------
# Task 5: Slide-7 lock allows bracket placeholder substitution
# ---------------------------------------------------------------------------

def test_slide_7_lock_permits_bracket_substitution():
    """
    The v3 template puts a [company] placeholder on slide 7
    ("Stakeholder Map: Role Profile Alignment"). The lock instruction
    we send to Gamma must explicitly permit bracket substitution while
    still preventing new content sections from being generated.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    company = {
        "company_name": "BC Liquor Distribution Branch",
        "validated_data": {"company_name": "BC Liquor Distribution Branch"},
    }
    output = creator._format_for_template(company)

    # Lock should still be present so Gamma doesn't generate new sections.
    assert "slide 7" in output.lower() and "lock" in output.lower(), (
        "slide-7 lock instruction must still be present in the inputText"
    )
    # New wording must explicitly mention bracket substitution.
    assert "bracket" in output.lower() or "[company]" in output, (
        "lock wording must explicitly permit [company] / bracket substitution"
    )
    # Reassuring keyword: substitution is not modification.
    assert "substitut" in output.lower(), (
        "expected wording that distinguishes substitution from modification"
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v -k slide_7_lock
```

Expected: FAIL — current wording does not mention "bracket" or "substitut".

- [ ] **Step 3: Implement the wording update**

In `backend/worker/gamma_slideshow.py`, find both occurrences (lines 253 and 648) of the slide-7 lock string. The current text reads:

```
ONLY slide 7 ("Stakeholder Map: Role Profile Alignment") is LOCKED. Do NOT generate, modify, or add any content on slide 7. Use its existing template layout exactly as-is with zero changes.
```

Replace **both occurrences** with:

```
ONLY slide 7 ("Stakeholder Map: Role Profile Alignment") has its LAYOUT locked. Do NOT generate, modify, or add any content sections on slide 7 — its existing template layout is final. However, bracket placeholders on slide 7 (e.g. [company], [name], [title]) MUST be substituted with the appropriate values from the data sections above. Substitution is not modification.
```

Make the same edit at line 648 — keep the surrounding warning-emoji prefix (`⚠️ REMINDER:` or similar) intact, just replace the body.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v
```

Expected: all tests PASS (13 total).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/RADTest && git add backend/worker/gamma_slideshow.py backend/tests/test_gamma_template_v3.py
git commit -m "$(cat <<'EOF'
fix(gamma): slide-7 lock wording permits bracket substitution

The v3 template introduces a [company] placeholder on slide 7. The
existing lock instruction said "Do NOT modify content on slide 7"
which Gamma's template engine could interpret as "don't substitute
either". Refines the wording at both occurrences to explicitly permit
bracket substitution while preserving the no-new-content guarantee.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Canonical stakeholder picker (`_pick_canonical_stakeholders`)

This is the largest task. It introduces a new private helper that selects up to 4 stakeholders (one each for CTO/CFO/CIO/COO with documented fallback rules), and replaces the old `1 best per csuiteCategory + otherContacts` logic at `gamma_slideshow.py:593-650`.

**Files:**
- Modify: `backend/worker/gamma_slideshow.py` — add private helper near other private methods on `GammaSlideshowCreator`; replace the existing stakeholder-merging block at lines 593-650
- Modify: `backend/tests/test_gamma_template_v3.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
# ---------------------------------------------------------------------------
# Task 6: _pick_canonical_stakeholders — 4-role canonical picker with
# tiered CIO/CISO fallback and seniority ranking
# ---------------------------------------------------------------------------

def _stake(name, title, csuite=None, email="", phone="", linkedin=""):
    return {
        "name": name,
        "title": title,
        "csuiteCategory": csuite,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
    }


def test_picker_returns_all_four_when_csuite_categories_match():
    """
    With direct csuiteCategory matches for CTO, CFO, CIO, COO, the picker
    returns exactly those 4 in CTO → CFO → CIO → COO order.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    sm = {
        "stakeholders": [
            _stake("Alice CFO",  "Chief Financial Officer", csuite="CFO"),
            _stake("Bob CIO",    "Chief Information Officer", csuite="CIO"),
            _stake("Carol COO",  "Chief Operating Officer",  csuite="COO"),
            _stake("Dan CTO",    "Chief Technology Officer", csuite="CTO"),
        ],
    }
    picked = creator._pick_canonical_stakeholders(sm)
    titles = [p["title"] for p in picked]
    assert titles == [
        "Chief Technology Officer",
        "Chief Financial Officer",
        "Chief Information Officer",
        "Chief Operating Officer",
    ]


def test_picker_skips_role_when_no_match_exists():
    """No COO match → 3 stakeholders returned, not 4 with a blank slot."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    sm = {
        "stakeholders": [
            _stake("CTO", "Chief Technology Officer", csuite="CTO"),
            _stake("CFO", "Chief Financial Officer",  csuite="CFO"),
            _stake("CIO", "Chief Information Officer", csuite="CIO"),
        ],
    }
    picked = creator._pick_canonical_stakeholders(sm)
    assert len(picked) == 3


def test_picker_falls_back_to_title_keywords_when_csuite_missing():
    """
    No csuiteCategory tags at all — picker uses title-keyword matching.
    "VP of Operations" fills COO; "Director of Information Technology" fills CIO.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    sm = {
        "stakeholders": [
            _stake("Tech",  "VP of Engineering"),         # → CTO
            _stake("Money", "VP of Finance"),             # → CFO
            _stake("Info",  "Director of Information Technology"),  # → CIO
            _stake("Ops",   "VP of Operations"),          # → COO
        ],
    }
    picked = creator._pick_canonical_stakeholders(sm)
    assert {p["name"] for p in picked} == {"Tech", "Money", "Info", "Ops"}


def test_picker_seniority_ranks_higher_when_multiple_match():
    """
    When multiple contacts match the same role, prefer Chief > VP > Director.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    sm = {
        "stakeholders": [
            _stake("Junior",  "Director of Operations"),
            _stake("Mid",     "VP of Operations"),
            _stake("Senior",  "Chief Operating Officer"),
        ],
    }
    picked = creator._pick_canonical_stakeholders(sm)
    coo_pick = [p for p in picked if p["name"] == "Senior"]
    assert coo_pick, f"expected Chief to win COO slot, got {[p['name'] for p in picked]}"


def test_picker_dedupes_same_person_across_slots():
    """
    A contact whose title matches both CTO and CIO keywords (e.g.,
    "Chief Technology and Information Officer") fills the earlier slot
    only; the later slot then looks for its own next-best match.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    sm = {
        "stakeholders": [
            _stake("Combo", "Chief Technology and Information Officer"),
            _stake("Backup CIO", "VP Information Technology"),
        ],
    }
    picked = creator._pick_canonical_stakeholders(sm)
    names = [p["name"] for p in picked]
    # "Combo" takes CTO; "Backup CIO" takes CIO.
    assert "Combo" in names
    assert names.count("Combo") == 1, (
        f"contact must not appear twice across slots, got {names}"
    )


def test_picker_ciso_only_fills_cio_when_no_cio_exists():
    """
    Tier-3 CISO fallback: when the only "Information"-titled person is a
    CISO and no other CIO match exists, the CISO fills the CIO slot.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    sm = {
        "stakeholders": [
            _stake("CTO Person",  "Chief Technology Officer", csuite="CTO"),
            _stake("CISO Person", "Chief Information Security Officer", csuite="CISO"),
        ],
    }
    picked = creator._pick_canonical_stakeholders(sm)
    cio_pick = [p for p in picked if "Security" in p["title"]]
    assert cio_pick, "CISO should fall back into CIO slot when no real CIO exists"


def test_picker_ciso_does_not_displace_real_cio():
    """
    When both a CIO and a CISO are present, the real CIO takes the CIO
    slot; the CISO is dropped (no separate CISO slide).
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    sm = {
        "stakeholders": [
            _stake("Real CIO",  "Chief Information Officer", csuite="CIO"),
            _stake("CISO",      "Chief Information Security Officer", csuite="CISO"),
        ],
    }
    picked = creator._pick_canonical_stakeholders(sm)
    cio_titles = [p["title"] for p in picked]
    assert "Chief Information Officer" in cio_titles
    assert "Chief Information Security Officer" not in cio_titles


def test_picker_uses_other_contacts_as_candidate_pool_only():
    """
    otherContacts are eligible candidates for canonical-role fallback
    but never get their own slides directly. A "VP Operations" listed
    in otherContacts (not in stakeholders) MUST be eligible for COO.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    sm = {
        "stakeholders": [
            _stake("CTO Only", "Chief Technology Officer", csuite="CTO"),
        ],
        "otherContacts": [
            _stake("From Other", "VP of Operations"),
        ],
    }
    picked = creator._pick_canonical_stakeholders(sm)
    names = [p["name"] for p in picked]
    assert "From Other" in names, (
        f"otherContacts must be eligible as canonical-role candidates, got {names}"
    )
    # And they don't show up twice (no separate "otherContacts" slide).
    assert names.count("From Other") == 1


def test_picker_returns_empty_list_when_no_data():
    """Empty stakeholder_map and no fallbacks → empty list."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    assert creator._pick_canonical_stakeholders({}) == []
    assert creator._pick_canonical_stakeholders({"stakeholders": []}) == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v -k picker
```

Expected: all 9 picker tests FAIL with `AttributeError: '...' object has no attribute '_pick_canonical_stakeholders'`.

- [ ] **Step 3: Implement the helper**

In `backend/worker/gamma_slideshow.py`, add the helper as a method on `GammaSlideshowCreator` (place it near `_format_for_template`, before the stakeholder-merging logic that's about to be replaced). Insert this code:

```python
    # Canonical-role title-keyword maps (v3 template).
    # "information" is intentionally NOT a CIO keyword — it would
    # otherwise pull CISO titles into the CIO slot. CISO is handled
    # via Tier 3 fallback (see _pick_canonical_stakeholders).
    _CANONICAL_ROLES = ["CTO", "CFO", "CIO", "COO"]
    _ROLE_KEYWORDS = {
        "CTO": ["chief technology officer", "vp engineering", "vp technology",
                "head of engineering", "head of technology", "technology",
                "engineering", "digital", "innovation", "architect"],
        "CFO": ["chief financial officer", "vp finance", "head of finance",
                "finance", "financial", "treasurer", "controller", "accounting"],
        "CIO": ["chief information officer", "vp information", "head of it",
                "vp of it", "director of it", "infrastructure",
                "information technology", "it ", "systems", "data"],
        "COO": ["chief operating officer", "vp operations", "head of operations",
                "vp of operations", "director of operations",
                "operations", "operating", "field services", "service delivery"],
    }
    _CISO_KEYWORDS = ["chief information security", "ciso",
                      "information security officer"]
    _SENIORITY_RANKS = [
        "chief", "svp", "evp", "senior vice president",
        "executive vice president", "vp", "vice president",
        "head of", "director", "manager",
    ]

    def _seniority_score(self, title: str) -> int:
        """Lower = more senior. Returns large int when no rank matches."""
        if not title:
            return 99
        t = title.lower()
        for i, rank in enumerate(self._SENIORITY_RANKS):
            if rank in t:
                return i
        return 99

    def _matches_role(self, title: str, role: str) -> bool:
        if not title:
            return False
        t = title.lower()
        for kw in self._ROLE_KEYWORDS[role]:
            if kw in t:
                return True
        return False

    def _is_security_title(self, title: str) -> bool:
        if not title:
            return False
        t = title.lower()
        return "security" in t or "ciso" in t

    def _is_ciso_title(self, title: str) -> bool:
        if not title:
            return False
        t = title.lower()
        return any(kw in t for kw in self._CISO_KEYWORDS)

    def _pick_canonical_stakeholders(
        self,
        stakeholder_map: Dict[str, Any],
        fallback_profiles: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns up to 4 contacts — one each for CTO/CFO/CIO/COO in that
        order. Skips a role if no plausible match exists in the entire
        candidate pool. See spec for the tiered selection rules.
        """
        # Build candidate pool: stakeholders + otherContacts + fallback_profiles
        candidates: List[Dict[str, Any]] = []
        if stakeholder_map:
            for c in (stakeholder_map.get("stakeholders") or []):
                if isinstance(c, dict):
                    candidates.append(c)
            for c in (stakeholder_map.get("otherContacts") or []):
                if isinstance(c, dict):
                    candidates.append(c)
        for c in (fallback_profiles or []):
            if isinstance(c, dict):
                candidates.append(c)
        if not candidates:
            return []

        chosen_ids = set()
        results: List[Dict[str, Any]] = []

        for role in self._CANONICAL_ROLES:
            best = None
            best_score = (99, 99)  # (tier, seniority) — lower is better
            for c in candidates:
                if id(c) in chosen_ids:
                    continue
                cat = (c.get("csuiteCategory") or "").upper()
                title = c.get("title") or ""
                seniority = self._seniority_score(title)

                if role == "CIO":
                    # Tier 1: csuiteCategory == 'CIO'
                    if cat == "CIO":
                        score = (1, seniority)
                    # Tier 2: title-keyword match excluding security titles
                    elif self._matches_role(title, "CIO") and not self._is_security_title(title):
                        score = (2, seniority)
                    # Tier 3: CISO fallback (last resort only)
                    elif self._is_ciso_title(title):
                        score = (3, seniority)
                    else:
                        continue
                else:
                    # Other roles: 2-tier — direct csuiteCategory or keyword match
                    if cat == role:
                        score = (1, seniority)
                    elif self._matches_role(title, role):
                        score = (2, seniority)
                    else:
                        continue

                if score < best_score:
                    best_score = score
                    best = c

            if best is not None:
                chosen_ids.add(id(best))
                results.append(best)

        return results
```

Then **replace** the existing stakeholder-merging block at `gamma_slideshow.py:593-650` (the `# 1. Executive stakeholders — pick 1 best per csuiteCategory` block plus the `# Other relevant contacts` block plus the legacy fallback). Replace the full ~57-line block with:

```python
        # v3: deterministic canonical 4-role picker (CTO/CFO/CIO/COO).
        # otherContacts and legacy stakeholder_profiles are candidate
        # sources only — they never get their own slides.
        legacy_profiles = validated_data.get('stakeholder_profiles', [])
        if isinstance(legacy_profiles, dict):
            # Old shape: dict keyed by role_type — flatten to list.
            flat = []
            for role_type, profile in legacy_profiles.items():
                if isinstance(profile, dict):
                    entry = {**profile}
                    if not entry.get('csuiteCategory'):
                        entry['csuiteCategory'] = role_type
                    flat.append(entry)
            legacy_profiles = flat
        elif not isinstance(legacy_profiles, list):
            legacy_profiles = []

        all_stakeholders = self._pick_canonical_stakeholders(
            stakeholder_map,
            fallback_profiles=legacy_profiles,
        )
```

(Adapt variable names to match the surrounding scope. The existing code probably already had `all_stakeholders` as the eventual name — preserve that name so downstream emission code is untouched. If the surrounding code uses different names, update the local variable to match.)

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v
```

Expected: all tests PASS (22 total: prior 13 + 9 picker tests).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/RADTest && git add backend/worker/gamma_slideshow.py backend/tests/test_gamma_template_v3.py
git commit -m "$(cat <<'EOF'
feat(gamma): canonical 4-role stakeholder picker with CISO fallback

Replaces the old "1 best per csuiteCategory + unbounded otherContacts"
selection with a deterministic 4-role picker (CTO/CFO/CIO/COO in that
exact order). Each slot uses tiered selection: direct csuiteCategory
match, then title-keyword match by seniority. The CIO slot uses an
extra Tier 3 — CISO titles fill it only when no CIO exists in the
entire candidate pool. otherContacts and legacy stakeholder_profiles
become candidate sources only (no separate slides). Skips a slot when
nothing plausible matches.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Stakeholder profile slide structure (Contact name+title separation)

**Files:**
- Modify: `backend/worker/gamma_slideshow.py` — per-stakeholder slide emission block (search for the loop that emits each stakeholder; after Task 6 it iterates over the canonical-picker output)
- Modify: `backend/tests/test_gamma_template_v3.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
# ---------------------------------------------------------------------------
# Task 7: Stakeholder profile structure — name + title separated under Contact
# ---------------------------------------------------------------------------

def test_stakeholder_profile_emits_name_and_title_separately():
    """
    Each stakeholder profile slide emits **name** on its own line and
    title on the next line under a "Contact" subheading.
    """
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    company = {
        "company_name": "Acme",
        "validated_data": {
            "company_name": "Acme",
            "stakeholder_map": {
                "stakeholders": [
                    {"name": "Jane Doe",
                     "title": "Chief Technology Officer",
                     "csuiteCategory": "CTO",
                     "email": "jane@acme.com"},
                ],
            },
        },
    }
    output = creator._format_for_template(company)
    # name and title on separate lines under Contact heading
    assert "**Jane Doe**" in output
    # The title line should be its own line, not concatenated with the name.
    assert "Jane Doe\nChief Technology Officer" in output or \
           "**Jane Doe**\nChief Technology Officer" in output, (
        "name and title must appear on separate consecutive lines"
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v -k stakeholder_profile_emits_name_and_title
```

Expected: FAIL — current emission concatenates name and title (e.g., `Jane Doe — Chief Technology Officer`).

- [ ] **Step 3: Implement the structural change**

In `backend/worker/gamma_slideshow.py`, find the loop that iterates over `all_stakeholders` and emits per-contact slide content (likely starts around `gamma_slideshow.py:647` after Task 6's replacement; search for where each stakeholder's name and title are formatted into the markdown). The current line probably looks like one of:

```python
data += f"**{name}** — {title}\n"
# or
data += f"{name} ({title})\n"
```

Replace with the v3 split-line format under a Contact heading:

```python
data += f"### Contact\n"
data += f"**{name}**\n"
data += f"{title}\n\n"
```

Adjust the heading level (`###` vs. `##`) to match the surrounding section's existing style.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v
```

Expected: all tests PASS (23 total).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/RADTest && git add backend/worker/gamma_slideshow.py backend/tests/test_gamma_template_v3.py
git commit -m "$(cat <<'EOF'
feat(gamma): stakeholder profiles emit name+title on separate lines

The v3 template's per-stakeholder slide has [name] and [title]
placeholders under a Contact subheading that need to address them
independently. Splits the previously-concatenated emission into two
separate lines so Gamma's template engine binds them correctly.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Communication preferences filter

**Files:**
- Modify: `backend/worker/gamma_slideshow.py` — communication-preferences emission inside the per-stakeholder loop
- Modify: `backend/tests/test_gamma_template_v3.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
# ---------------------------------------------------------------------------
# Task 8: Communication preferences filter — Email | Phone | LinkedIn,
# omit empty channels, preserve order
# ---------------------------------------------------------------------------

def test_comm_prefs_all_three_channels_populated():
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    company = {
        "company_name": "Acme",
        "validated_data": {
            "company_name": "Acme",
            "stakeholder_map": {
                "stakeholders": [
                    {"name": "All Channels", "title": "Chief Technology Officer",
                     "csuiteCategory": "CTO",
                     "email": "all@acme.com",
                     "phone": "+1-555-1234",
                     "linkedin": "https://linkedin.com/in/all"},
                ],
            },
        },
    }
    output = creator._format_for_template(company)
    # All three channels present in Email → Phone → LinkedIn order.
    idx_email = output.find("Email:")
    idx_phone = output.find("Phone:")
    idx_li = output.find("LinkedIn:")
    assert idx_email >= 0 and idx_phone >= 0 and idx_li >= 0
    assert idx_email < idx_phone < idx_li, (
        f"comm prefs must be ordered Email→Phone→LinkedIn; "
        f"got positions {idx_email}, {idx_phone}, {idx_li}"
    )


def test_comm_prefs_skips_empty_channels():
    """A contact with email + linkedin but no phone shows 2 bullets, not 3."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    company = {
        "company_name": "Acme",
        "validated_data": {
            "company_name": "Acme",
            "stakeholder_map": {
                "stakeholders": [
                    {"name": "No Phone", "title": "Chief Technology Officer",
                     "csuiteCategory": "CTO",
                     "email": "np@acme.com",
                     "phone": "",
                     "linkedin": "https://linkedin.com/in/np"},
                ],
            },
        },
    }
    output = creator._format_for_template(company)
    # Find the per-stakeholder slide block — Phone line must not appear in it.
    section = output[output.find("**No Phone**"):]
    # Cut to a generous window
    section = section[:1500]
    assert "Phone:" not in section, (
        "empty phone channel must not render a Phone: bullet"
    )
    assert "Email: np@acme.com" in section
    assert "LinkedIn: https://linkedin.com/in/np" in section


def test_comm_prefs_only_email_present():
    from worker.gamma_slideshow import GammaSlideshowCreator
    creator = GammaSlideshowCreator(gamma_api_key="test-key")
    company = {
        "company_name": "Acme",
        "validated_data": {
            "company_name": "Acme",
            "stakeholder_map": {
                "stakeholders": [
                    {"name": "Email Only", "title": "Chief Technology Officer",
                     "csuiteCategory": "CTO",
                     "email": "eo@acme.com",
                     "phone": "",
                     "linkedin": ""},
                ],
            },
        },
    }
    output = creator._format_for_template(company)
    section = output[output.find("**Email Only**"):]
    section = section[:1500]
    assert "Email: eo@acme.com" in section
    assert "Phone:" not in section
    assert "LinkedIn:" not in section
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v -k comm_prefs
```

Expected: 3 FAIL — current emission likely doesn't filter or doesn't use this exact format.

- [ ] **Step 3: Implement the comm-prefs emission**

In `backend/worker/gamma_slideshow.py`, find the block inside the per-stakeholder loop where contact channels are emitted. The existing code may emit phone/email/linkedin directly without filtering, or with a different label set.

Replace with a filtered, ordered list:

```python
        # v3 communication preferences: Email | Phone | LinkedIn order,
        # only render channels with populated values.
        email_val = (s.get('email') or '').strip()
        # Phone fallback chain preserved from earlier commit 198d20a:
        # top-level → contact dict → company_phone.
        phone_val = (s.get('phone')
                     or (s.get('contact') or {}).get('directPhone')
                     or (s.get('contact') or {}).get('mobilePhone')
                     or s.get('company_phone')
                     or s.get('companyPhone')
                     or '').strip()
        linkedin_val = (s.get('linkedin') or s.get('linkedinUrl') or '').strip()

        if email_val or phone_val or linkedin_val:
            data += "### Communication Preferences\n"
            if email_val:
                data += f"- Email: {email_val}\n"
            if phone_val:
                data += f"- Phone: {phone_val}\n"
            if linkedin_val:
                data += f"- LinkedIn: {linkedin_val}\n"
            data += "\n"
```

The variable name `s` should match the existing per-stakeholder loop variable — adapt to whatever the surrounding code uses (`stakeholder`, `contact`, `s`, etc.).

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v
```

Expected: all tests PASS (26 total).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/RADTest && git add backend/worker/gamma_slideshow.py backend/tests/test_gamma_template_v3.py
git commit -m "$(cat <<'EOF'
feat(gamma): communication-preferences filter for v3 template

The v3 template placeholder for comm prefs reads "[choose at least
one of (email/phone/linkedin) depending on which appropriate]".
Renders only the channels that have populated values for each
contact, in fixed Email→Phone→LinkedIn order. Preserves the phone
fallback chain established in commit 198d20a (top-level → contact
dict → company_phone).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Reinforce `recommended_solution_areas` LLM prompt

**Files:**
- Modify: `backend/llm_council.py:504-508`
- Modify: `backend/tests/test_gamma_template_v3.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
# ---------------------------------------------------------------------------
# Task 9: LLM prompt reinforcement — anti-SKU constraint in all 3 slots
# ---------------------------------------------------------------------------

def test_llm_prompt_anti_sku_constraint_in_all_three_slots():
    """
    The recommended_solution_areas prompt block must repeat the no-SKU
    constraint in all three slot descriptions. Read the source of
    backend/llm_council.py and assert the constraint marker appears
    at least 3 times within the recommended_solution_areas block.
    """
    import os, re
    # Tests run with cwd=backend, so resolve relative to the test file:
    # backend/tests/test_gamma_template_v3.py → ../llm_council.py
    src_path = os.path.join(os.path.dirname(__file__), "..", "llm_council.py")
    with open(src_path) as f:
        src = f.read()

    # Extract the recommended_solution_areas list block.
    m = re.search(
        r'"recommended_solution_areas"\s*:\s*\[(.*?)\]\s*\}\}',
        src, re.DOTALL,
    )
    assert m, "could not locate recommended_solution_areas block in llm_council.py"
    block = m.group(1)

    # The reinforced prompt repeats the constraint in all 3 slot descriptions.
    # We accept any of these markers as evidence of the constraint:
    markers = ["MUST NOT", "product names", "no SKU", "no specific HP product"]
    occurrences = sum(block.count(marker) for marker in markers)
    assert occurrences >= 3, (
        f"expected the no-SKU constraint to appear in all 3 slots "
        f"(>=3 marker occurrences), found {occurrences}. Block:\n{block}"
    )

    # Concrete examples should be in the prompt as further reinforcement.
    assert "endpoint security posture" in block.lower() or \
           "ai-ready" in block.lower() or \
           "managed device lifecycle" in block.lower(), (
        "expected at least one concrete acceptable-title example in the prompt"
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v -k llm_prompt
```

Expected: FAIL — current prompt has the constraint only in slot #1, slots #2 and #3 are minimal ("3-5 sentence high-level HP strategic rationale.").

- [ ] **Step 3: Update the prompt**

In `backend/llm_council.py`, find the block at lines 504-508 (search for `"recommended_solution_areas":`). Replace with:

```python
        "recommended_solution_areas": [
            {{"title": "High-level HP strategic area (broad capability category)", "description": "3-5 sentence explanation of how to position HP as a strategic partner in this area. MUST be a broad capability category — NOT a specific HP product line, SKU, or model number. Acceptable titles: 'endpoint security posture', 'AI-ready workstation fleet', 'managed device lifecycle', 'hybrid-work device strategy'. Unacceptable titles: 'HP Wolf Pro Security Service', 'HP Z by HP', 'HP EliteBook 840 G10', 'HP Anyware'. Frame as high-level ways HP can help — e.g. device standardization, endpoint security posture, lifecycle management, workplace modernization. Write from the perspective of giving a salesperson strategic framing they can run with."}},
            {{"title": "Second HP strategic area (broad capability category — MUST NOT be a product name or SKU)", "description": "3-5 sentence high-level HP strategic rationale. Title MUST be a broad capability category, never a specific HP product name, SKU, or model number."}},
            {{"title": "Third HP strategic area (broad capability category — MUST NOT be a product name or SKU)", "description": "3-5 sentence high-level HP strategic rationale. Title MUST be a broad capability category, never a specific HP product name, SKU, or model number."}}
        ]
```

Schema and field name are unchanged — only the constraint wording is strengthened and propagated to all three slots.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v
```

Expected: all tests PASS (27 total).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/RADTest && git add backend/llm_council.py backend/tests/test_gamma_template_v3.py
git commit -m "$(cat <<'EOF'
feat(llm): repeat no-SKU constraint across all 3 solution slots

Strengthens the recommended_solution_areas prompt to reduce LLM drift
toward niche HP product titles. The constraint ("MUST NOT be a
product name or SKU") now appears in all three slot descriptions —
previously only slot #1 had it. Adds concrete acceptable / unacceptable
title examples inside slot #1 for the LLM to pattern-match against.
Schema and field name are unchanged.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Final regression sweep + version tag bump

**Files:**
- Modify: `backend/production_main.py` — `deploy_version` string in `/health` response (search for the existing `"deploy_version": "hp-outreach-templates-v2"` and bump to `"gamma-template-v3"` so we can verify the new code is live on Render)
- No new tests; runs the existing suites

- [ ] **Step 1: Run the full new-feature suite**

```bash
cd backend && python3 -m pytest tests/test_gamma_template_v3.py -v
```

Expected: all 27 tests PASS.

- [ ] **Step 2: Run the prior pending-recovery suite (regression check)**

```bash
cd backend && python3 -m pytest tests/test_gamma_pending_recovery.py -v
```

Expected: all 11 tests PASS — the changes in this plan must not break the pending-recovery infrastructure.

- [ ] **Step 3: Bump the deploy version tag**

In `backend/production_main.py`, search for `deploy_version` (currently `"hp-outreach-templates-v2"`). Update to `"gamma-template-v3"` so post-deploy `curl /health` will confirm the new revision is live.

```python
"deploy_version": "gamma-template-v3"
```

- [ ] **Step 4: Run a syntax-check on the two modified production files**

```bash
python3 -c "import ast; ast.parse(open('/workspaces/RADTest/backend/worker/gamma_slideshow.py').read()); print('gamma_slideshow.py: OK')"
python3 -c "import ast; ast.parse(open('/workspaces/RADTest/backend/llm_council.py').read()); print('llm_council.py: OK')"
python3 -c "import ast; ast.parse(open('/workspaces/RADTest/backend/production_main.py').read()); print('production_main.py: OK')"
```

Expected: all three print `OK`.

- [ ] **Step 5: Commit and push**

```bash
cd /workspaces/RADTest && git add backend/production_main.py
git commit -m "$(cat <<'EOF'
chore(deploy): bump deploy_version to gamma-template-v3

Post-deploy /health check will reflect the new revision once Render
auto-deploy finishes building the v3 changes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

(Push is left to the user / driving session — see Acceptance below.)

---

## Acceptance

Final state after Task 10 commits:

1. `backend/tests/test_gamma_template_v3.py` exists with 27 passing tests.
2. `backend/tests/test_gamma_pending_recovery.py` still has 11 passing tests (no regression).
3. `GammaSlideshowCreator` defaults to `template_id="g_uost7x0lutmwtwd"`.
4. `_normalize_account_type()` exists at module level and routes 5 LLM buckets → 4 template buckets.
5. Pain-points and sales-opportunities sections emit bolded titles + blank-line + paragraph in both `_format_for_template` and `_generate_markdown` paths.
6. Slide-7 lock instruction explicitly permits bracket substitution at lines 253 and 648.
7. `_pick_canonical_stakeholders()` returns up to 4 contacts in CTO→CFO→CIO→COO order with the documented tiered selection rules; old `otherContacts`-as-slides emission is gone.
8. Per-stakeholder slides emit `name` and `title` on separate lines under a Contact heading.
9. Communication preferences emit a filtered Email→Phone→LinkedIn list (no empty bullets).
10. `backend/llm_council.py:504-508` carries the no-SKU constraint in all 3 slot descriptions.
11. `/health` reports `deploy_version: "gamma-template-v3"` after the next Render deploy.

A regenerated BC Liquor Distribution Branch deck against the v3 template should:
- Render `Government` in the executive snapshot account-type field
- Show 3 pain points, each with bolded title and separate description paragraph
- Show 3 sales opportunities, each numbered with bolded title and separate validation blurb
- Show "Key Decision Makers at BC Liquor Distribution Branch" on slide 7 (auto-substituted by Gamma)
- Show ≤4 stakeholder profile slides — best-fit CTO/CFO/CIO/COO with CISO falling back to CIO only if no CIO contact exists
- Each profile shows name/title on separate lines, plus a populated-channels-only comm-prefs list
- Show recommended-solution titles at capability-category granularity, never SKU level
