#!/usr/bin/env python3
"""
Deterministic master-template editor (v3.1 slideshow QA).

python-pptx is NOT available in this environment, so this performs the edits via
the OOXML zip + XML directly (a .pptx is a zip of XML parts). Every edit asserts
its expected match count and FAILS LOUD on drift, so a template change can never
silently no-op. It does NOT render — visual sizing is reviewed in the output deck
after re-upload (see the hand-off command printed by this script).

Edits applied (logged QA defects):
  #4 slide5  Opportunity Themes: split each theme's single bracket token that
             spans the bold-header paragraph + unbold-body paragraph into TWO
             self-contained tokens ([header] / [body]). The renderer's existing
             per-paragraph fill then preserves the numbering + bold header that
             the paragraph-spanning collapse used to destroy. (Text only.)
  #2 slide2  Executive Snapshot: grow the company-overview body box and push the
             "Installed technologies" block down so the overview stops bleeding
             into that header.
  #5 slide6  Sales Opportunities: enlarge the three opportunity boxes (and their
             body text frames) so copy stops bleeding out the bottom. Font sizes
             are left UNTOUCHED (kept consistent across slides — no autofit).
  #6 slide8  Stakeholder Profile: move "Strategic priorities" (header + body) and
             the "Conversation starters" block below it down, so the bleeding
             "About" text no longer overlaps the "Strategic priorities" header.

Usage:
  python3 scripts/edit_master_template.py [SRC_PPTX] [OUT_PPTX]
Defaults:
  SRC = "template /Account-Intelligence-Report Template for Claude to follow.pptx"
  OUT = "template /master-template.v31-edited.pptx"
"""
from __future__ import annotations

import os
import re
import sys
import zipfile

DEFAULT_SRC = "template /Account-Intelligence-Report Template for Claude to follow.pptx"
DEFAULT_OUT = "template /master-template.v31-edited.pptx"


def _replace_once(xml: str, old: str, new: str, *, expect: int, where: str) -> str:
    """Replace `old`→`new`, asserting exactly `expect` occurrences existed."""
    n = xml.count(old)
    if n != expect:
        raise SystemExit(f"[FAIL] {where}: expected {expect} match(es) of {old!r}, found {n}. "
                         f"Template drifted — aborting so nothing ships silently wrong.")
    return xml.replace(old, new)


def _scope_shape_replace(xml: str, marker: str, old: str, new: str, *, expect: int, where: str) -> str:
    """Replace `old`→`new` ONLY inside <p:sp> shapes whose text contains `marker`.

    Lets a font/size tweak target a specific block (e.g. the right-column body
    text frames) without touching identical strings elsewhere on the slide.
    Asserts exactly `expect` shapes matched, FAILING LOUD on drift."""
    hits = [0]

    def fix(m: re.Match) -> str:
        sp = m.group(0)
        if marker not in sp:
            return sp
        hits[0] += 1
        return sp.replace(old, new)

    out = re.sub(r"<p:sp>.*?</p:sp>", fix, xml, flags=re.S)
    if hits[0] != expect:
        raise SystemExit(f"[FAIL] {where}: expected {expect} shape(s) containing {marker!r}, "
                         f"found {hits[0]}. Template drifted — aborting.")
    return out


def _move_bracket_into_value_run(xml: str, label: str, *, expect: int, where: str) -> str:
    """Move the literal '[' out of a bold '<label> [' run into the start of the
    following (unbold) value run.

    The master authors several detail lines as `<bold>"Label: ["</bold>` +
    `<unbold>"value]"</unbold>`. Because the token's '[' lives in the BOLD run,
    the renderer's span-aware fill places the value in that bold run — bolding
    the whole value. Pulling the '[' into the value run makes the token sit
    wholly in the unbold run, so the value renders unbold (the label stays bold)."""
    pat = re.compile(r"<a:t>" + re.escape(label) + r" \[</a:t>(</a:r><a:r>.*?<a:t>)", re.S)
    out, n = pat.subn(r"<a:t>" + label + r" </a:t>\1[", xml)
    if n != expect:
        raise SystemExit(f"[FAIL] {where}: expected {expect} '{label} [' bracket-move(s), got {n}.")
    return out


# --- #4 Opportunity Themes token split (slide5) ------------------------------

def edit_slide5(xml: str) -> str:
    """Close the bracket on each numbered header run and open one on each body
    run, turning a paragraph-spanning token into two single-paragraph tokens."""
    headers = 0
    bodies = 0

    def fix_run(m: re.Match) -> str:
        nonlocal headers, bodies
        text = m.group(1)
        opens = text.startswith("[")
        closes = text.rstrip().endswith("]")
        if opens and not closes:        # header: "[Need for Enhanced ..." -> add "]"
            headers += 1
            return f"<a:t>{text}]</a:t>"
        if closes and not opens:        # body: "Aviva ... improvement.]" -> add "["
            bodies += 1
            return f"<a:t>[{text}</a:t>"
        return m.group(0)

    out = re.sub(r"<a:t>(.*?)</a:t>", fix_run, xml, flags=re.S)
    if (headers, bodies) != (6, 6):
        raise SystemExit(f"[FAIL] slide5 #4: expected to split 6 headers + 6 bodies, "
                         f"got {headers} + {bodies}. Aborting.")
    # NOTE: the blank auto-numbered spacer paragraph between points is KEPT — at
    # 7.5pt the bodies fit with the line breaks in place, and the user prefers the
    # visual separation between points (an earlier batch removed them; reverted).
    return out


# --- #1 Key Signals: unbold the 2nd signal's "What this means" value (slide4) --

def edit_slide4(xml: str) -> str:
    """The 1st signal puts the whole [token] in its (unbold) value run and renders
    correctly; the 2nd signal authored the open bracket INSIDE the bold
    "What this means: [" run, so the value rendered bold. Move the '[' into the
    value run so the 2nd signal matches the 1st (bold label, unbold value)."""
    xml = _move_bracket_into_value_run(xml, "What this means:", expect=1, where="slide4 #1")
    # Extend both signal panels + their body text frames DOWN so the longer
    # "What this means" copy stops overflowing the bottom of the panel. The two
    # colored panels start at y=1476970 and the body frames at y=2285479; grow
    # them toward the slide bottom (5143500) leaving a ~0.17" margin. (Concise
    # titles are handled by the formatter prompt; this is purely the body bleed.)
    xml = _replace_once(xml,  # col1 panel: cy -> bottom ~4980000
        '<a:ext cx="2303934" cy="3083496"/>', '<a:ext cx="2303934" cy="3503030"/>',
        expect=1, where="slide4 #1 col1 panel height")
    xml = _replace_once(xml,  # col2 panel
        '<a:ext cx="2304008" cy="3083496"/>', '<a:ext cx="2304008" cy="3503030"/>',
        expect=1, where="slide4 #1 col2 panel height")
    xml = _replace_once(xml,  # col1 body frame: cy -> bottom ~4950000
        '<a:ext cx="2020267" cy="2133154"/>', '<a:ext cx="2020267" cy="2664521"/>',
        expect=1, where="slide4 #1 col1 body height")
    xml = _replace_once(xml,  # col2 body frame
        '<a:ext cx="2020342" cy="2133154"/>', '<a:ext cx="2020342" cy="2664521"/>',
        expect=1, where="slide4 #1 col2 body height")
    return xml


# --- #2 Executive Snapshot spacing (slide2) ----------------------------------

def edit_slide2(xml: str) -> str:
    xml = _replace_once(xml,  # overview body box: 1604665 -> 1900000 EMU tall
        '<a:ext cx="2214414" cy="1604665"/>', '<a:ext cx="2214414" cy="1900000"/>',
        expect=1, where="slide2 #2 overview body height")
    xml = _replace_once(xml,  # "Installed technologies" header: y 3249737 -> 3650000
        '<a:off x="6438230" y="3249737"/>', '<a:off x="6438230" y="3650000"/>',
        expect=1, where="slide2 #2 installed-tech header y")
    xml = _replace_once(xml,  # installed-tech body: y 3540398 -> 3950000
        '<a:off x="6438230" y="3540398"/>', '<a:off x="6438230" y="3950000"/>',
        expect=1, where="slide2 #2 installed-tech body y")
    return xml


# --- #5 Sales Opportunities box enlargement (slide6) -------------------------

def edit_slide6(xml: str) -> str:
    xml = _replace_once(xml,  # the 3 opportunity boxes: cy 2399184 -> 3000000
        '<a:ext cx="2622724" cy="2399184"/>', '<a:ext cx="2622724" cy="3000000"/>',
        expect=3, where="slide6 #5 box height (x3)")
    xml = _replace_once(xml,  # 2 body text frames: cy 1360884 -> 1900000
        '<a:ext cx="2339206" cy="1360884"/>', '<a:ext cx="2339206" cy="1900000"/>',
        expect=2, where="slide6 #5 body text height (x2)")
    xml = _replace_once(xml,  # 1 body text frame: cy 1587698 -> 1900000
        '<a:ext cx="2339206" cy="1587698"/>', '<a:ext cx="2339206" cy="1900000"/>',
        expect=1, where="slide6 #5 body text height (x1)")
    return xml


# --- #6 Stakeholder "Strategic priorities" reposition (slide8) ---------------

def edit_slide8(xml: str) -> str:
    # Shift "Strategic priorities" (header+body) and "Conversation starters"
    # (header+body) down by 200000 EMU (~0.22"), widening the gap below the
    # "About" body so it stops overlapping the "Strategic priorities" header.
    for old_y, new_y, what in (
        ("2100039", "2300039", "strategic-priorities header"),
        ("2367930", "2567930", "strategic-priorities body"),
        ("3501628", "3701628", "conversation-starters header"),
        ("3769519", "3969519", "conversation-starters body"),
    ):
        xml = _replace_once(xml,
            f'<a:off x="4715098" y="{old_y}"/>', f'<a:off x="4715098" y="{new_y}"/>',
            expect=1, where=f"slide8 #6 {what} y")

    # #3 (this session) Strategic priorities should render as bullet points and
    # Conversation starters as a NUMBERED list. Strategic priorities already carry
    # buChar bullets across 3 paragraphs (the renderer now re-applies that pPr after
    # its frame-level fill), so no edit is needed there. Conversation starters are a
    # SINGLE plain paragraph — split into TWO numbered (buAutoNum) paragraphs so the
    # token spans paragraphs (triggering the renderer's frame-level path, which then
    # emits one numbered paragraph per starter and re-applies the buAutoNum pPr).
    xml = _split_conversation_into_numbered(xml)

    # About / Strategic / Conversation body copy overruns its frame: drop those
    # three right-column body text frames 8.5pt -> 7.5pt (scoped to the right column
    # cx="3937546" so left-column contact details stay 8.5pt). Runs added by the
    # conversation split above are sz="850" so they are caught here too.
    xml = _scope_shape_replace(xml, 'cx="3937546"', 'sz="850"', 'sz="750"',
                               expect=3, where="slide8 #3 right-column body font")
    return xml


def _split_conversation_into_numbered(xml: str) -> str:
    """Turn the single conversation-starters paragraph into two buAutoNum (numbered)
    paragraphs forming one paragraph-spanning token. Keeps the run's rPr so the font
    is preserved, and keeps the leading "[Engage Lisa by" so the renderer's prefix
    classifier still maps it to conversation_starters."""
    m = re.search(r'<a:p>(?:(?!</a:p>).)*?\[Engage Lisa by(?:(?!</a:p>).)*?</a:p>', xml, re.S)
    if not m:
        raise SystemExit("[FAIL] slide8 #3: conversation-starters paragraph not found")
    para = m.group(0)
    rpr = re.search(r'<a:rPr\b.*?</a:rPr>', para, re.S)
    if not rpr:
        raise SystemExit("[FAIL] slide8 #3: conversation run properties not found")
    rpr_xml = rpr.group(0)
    ppr = ('<a:pPr marL="342900" indent="-342900" algn="l"><a:lnSpc>'
           '<a:spcPct val="120000"/></a:lnSpc><a:buSzPct val="100000"/>'
           '<a:buAutoNum type="arabicPeriod"/></a:pPr>')
    end = '<a:endParaRPr lang="en-US" sz="850" dirty="0"/>'
    s1 = ("[Engage Lisa by demonstrating how your solution bridges technology and "
          "underwriting outcomes.")
    s2 = ("Lead with concrete examples of automation, data enrichment, or analytics "
          "capabilities that translate into measurable improvements in underwriting "
          "speed, accuracy, or loss ratio.]")
    new = (f'<a:p>{ppr}<a:r>{rpr_xml}<a:t>{s1}</a:t></a:r>{end}</a:p>'
           f'<a:p>{ppr}<a:r>{rpr_xml}<a:t>{s2}</a:t></a:r>{end}</a:p>')
    return xml[:m.start()] + new + xml[m.end():]


# --- #4 Recommended Sales Program: unbold "Why" + stop box bleed (slide9) -----

def edit_slide9(xml: str) -> str:
    # Unbold each box's "Why:" rationale by moving the '[' out of the bold
    # "Why: [" run into the (unbold) value run (4 boxes).
    xml = _move_bracket_into_value_run(xml, "Why:", expect=4, where="slide9 #4 Why unbold")
    # Text bleeding out of the boxes: drop the 4 collateral/Why body frames
    # 8.0pt -> 7.5pt so the copy fits inside the colored box. Scoped by the
    # "Marketing collateral:" label so only those bodies shrink.
    xml = _scope_shape_replace(xml, "Marketing collateral:", 'sz="800"', 'sz="750"',
                               expect=4, where="slide9 #4 body font")

    # Standardize the 4 panels to the (taller) bottom-row height so the top 2 stop
    # overflowing. The top boxes (920651) grow to match the bottom (1069479); to
    # keep both rows clear, nudge the top row UP 70000 EMU (clearing the subtitle)
    # and the bottom row DOWN 80000 EMU (still above "Supporting assets"). Each
    # panel's number label + body frame moves with its box (same delta).
    xml = _replace_once(xml, '<a:ext cx="4035996" cy="920651"/>',
                        '<a:ext cx="4035996" cy="1069479"/>', expect=1, where="slide9 #4 top-left panel cy")
    xml = _replace_once(xml, '<a:ext cx="4036070" cy="920651"/>',
                        '<a:ext cx="4036070" cy="1069479"/>', expect=1, where="slide9 #4 top-right panel cy")
    for x, old_y, new_y, what in (
        # top row up 70000: panels, "1."/"2." labels, body frames
        ("496119", "1313557", "1243557", "top-left panel"),
        ("4611812", "1313557", "1243557", "top-right panel"),
        ("602382", "1419820", "1349820", "label 1"),
        ("4718075", "1419820", "1349820", "label 2"),
        ("602382", "1633686", "1563686", "body 1"),
        ("4718075", "1633686", "1563686", "body 2"),
        # bottom row down 80000: panels, "3."/"4." labels, body frames
        ("496119", "2313905", "2393905", "bottom-left panel"),
        ("4611812", "2313905", "2393905", "bottom-right panel"),
        ("602382", "2420169", "2500169", "label 3"),
        ("4718075", "2420169", "2500169", "label 4"),
        ("602382", "2634035", "2714035", "body 3"),
        ("4718075", "2634035", "2714035", "body 4"),
    ):
        xml = _replace_once(xml, f'<a:off x="{x}" y="{old_y}"/>', f'<a:off x="{x}" y="{new_y}"/>',
                            expect=1, where=f"slide9 #4 {what} y")
    return xml


EDITS = {
    "ppt/slides/slide2.xml": edit_slide2,
    "ppt/slides/slide4.xml": edit_slide4,
    "ppt/slides/slide5.xml": edit_slide5,
    "ppt/slides/slide6.xml": edit_slide6,
    "ppt/slides/slide8.xml": edit_slide8,
    "ppt/slides/slide9.xml": edit_slide9,
}


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    out = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT
    if not os.path.exists(src):
        raise SystemExit(f"[FAIL] source template not found: {src}")

    with zipfile.ZipFile(src) as zin:
        names = zin.namelist()
        parts = {n: zin.read(n) for n in names}

    for part, fn in EDITS.items():
        if part not in parts:
            raise SystemExit(f"[FAIL] expected part missing from template: {part}")
        new_xml = fn(parts[part].decode("utf-8"))
        parts[part] = new_xml.encode("utf-8")
        print(f"  edited {part}")

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:  # preserve original part order
            zout.writestr(n, parts[n])

    # Re-open + structural self-check: token brackets on slide5 must now balance.
    with zipfile.ZipFile(out) as zchk:
        s5 = zchk.read("ppt/slides/slide5.xml").decode("utf-8")
    texts = re.findall(r"<a:t>(.*?)</a:t>", s5, re.S)
    joined = "".join(texts)
    if joined.count("[") != joined.count("]"):
        raise SystemExit(f"[FAIL] slide5 brackets unbalanced after edit: "
                         f"{joined.count('[')} '[' vs {joined.count(']')} ']'")
    tokens = re.findall(r"\[[^\[\]]+\]", joined)
    print(f"\nWrote {out}")
    print(f"slide5 now has {len(tokens)} self-contained tokens (was 6 spanning, now 12).")
    print("\nNEXT (manual — not run here, per the deploy rulebook):")
    print('  export SUPABASE_URL="https://lipdzdhpptfcvuswkcng.supabase.co"')
    print('  export SUPABASE_SERVICE_KEY="<service_role key — from env, do not paste>"')
    print(f'  ./scripts/upload-master-template.sh "{out}"')


if __name__ == "__main__":
    main()
