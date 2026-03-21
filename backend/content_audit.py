"""
Content Audit module.
Loads HP Canada content audit CSV, provides keyword-based matching for Gamma
slideshow integration, and supports user-added items at runtime.
"""
import csv
import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Module-level store: list of content audit dicts
_items: List[Dict[str, Any]] = []
_loaded = False

CSV_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "hp_assets",
    "HP Canada_RAD Intelligence Desk_Content Audit(Audit).csv",
)

# Column name mapping (CSV header -> internal key)
_COLUMN_MAP = {
    "Asset Name": "asset_name",
    "Industry": "industry",
    "Service/Solution": "service_solution",
    "Year Published": "year_published",
    "Audience": "audience",
    "Asset Summary": "asset_summary",
    "Ebook ": "ebook",
    "Format": "format",
    "Page Count": "page_count",
    "Marketing or Sales": "marketing_or_sales",
    "Consideration ": "consideration",
    "Inventory Recommendations": "inventory_recommendations",
    "SP Link": "sp_link",
    "Audit Notes": "audit_notes",
}


def load_content_audit(force: bool = False) -> None:
    """Load the HP Canada content audit CSV into memory.

    Args:
        force: Reload even if already loaded.
    """
    global _items, _loaded

    if _loaded and not force:
        return

    base_items: List[Dict[str, Any]] = []
    csv_path = os.path.normpath(CSV_PATH)

    if not os.path.exists(csv_path):
        logger.warning(f"Content audit CSV not found at {csv_path}")
        _items = []
        _loaded = True
        return

    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item: Dict[str, Any] = {"source": "csv"}
            for csv_col, key in _COLUMN_MAP.items():
                raw = row.get(csv_col, "").strip()
                # Clean up multiline values from the CSV
                raw = " ".join(raw.split())
                item[key] = raw
            # Skip rows with no asset name
            if item.get("asset_name"):
                item["id"] = len(base_items) + 1
                base_items.append(item)

    # Preserve any user-added items from a previous load
    user_items = [i for i in _items if i.get("source") == "user"]
    _items = base_items + user_items
    _loaded = True
    logger.info(f"Loaded {len(base_items)} content audit items from CSV, {len(user_items)} user items preserved")


def get_all_items() -> List[Dict[str, Any]]:
    """Return all content audit items (CSV + user-added)."""
    if not _loaded:
        load_content_audit()
    return list(_items)


def add_item(
    asset_name: str,
    sp_link: str,
    asset_summary: str,
    industry: str = "",
    service_solution: str = "",
    audience: str = "",
    format_type: str = "",
) -> Dict[str, Any]:
    """Add a user-defined content audit item.

    Returns:
        The newly created item dict.
    """
    if not _loaded:
        load_content_audit()

    new_id = max((i.get("id", 0) for i in _items), default=0) + 1
    item: Dict[str, Any] = {
        "id": new_id,
        "source": "user",
        "asset_name": asset_name,
        "sp_link": sp_link,
        "asset_summary": asset_summary,
        "industry": industry,
        "service_solution": service_solution,
        "audience": audience,
        "format": format_type,
        "year_published": "",
        "ebook": "",
        "page_count": "",
        "marketing_or_sales": "",
        "consideration": "",
        "inventory_recommendations": "",
        "audit_notes": "",
    }
    _items.append(item)
    logger.info(f"Added user content audit item: {asset_name}")
    return item


# ---------------------------------------------------------------------------
# Matching helpers for Gamma slideshow integration
# ---------------------------------------------------------------------------

def _score_item(item: Dict[str, Any], keywords: List[str], audience: str = "") -> float:
    """Score how well an item matches the given keywords and audience.

    Higher score = better match.
    """
    score = 0.0
    searchable = (
        (item.get("asset_name", "") + " " + item.get("asset_summary", "") + " " + item.get("service_solution", ""))
        .lower()
    )

    for kw in keywords:
        kw_lower = kw.lower().strip()
        if not kw_lower:
            continue
        # Exact phrase match worth more
        if kw_lower in searchable:
            score += 10.0
        else:
            # Check individual words
            for word in kw_lower.split():
                if len(word) > 2 and word in searchable:
                    score += 2.0

    # Audience match bonus
    if audience:
        item_audience = item.get("audience", "").strip().upper()
        if audience.upper() in item_audience:
            score += 5.0

    # Prefer "Leverage" items over "Upcycle" over "Retire"
    rec = item.get("inventory_recommendations", "").strip().lower()
    if "leverage" in rec:
        score += 3.0
    elif "upcycle" in rec:
        score += 1.0
    elif "retire" in rec:
        score -= 5.0

    # Prefer newer content
    year = item.get("year_published", "").strip()
    if year == "2025":
        score += 2.0
    elif year == "2024":
        score += 1.0

    return score


def match_content(
    keywords: List[str],
    audience: str = "",
    exclude_ids: Optional[List[int]] = None,
) -> Optional[Dict[str, Any]]:
    """Find the best matching content audit item for the given keywords.

    Args:
        keywords: Search terms to match against asset name, summary, and solution.
        audience: Preferred audience (e.g. "ITDM", "BDM").
        exclude_ids: Item IDs to skip (avoid duplicating across slots).

    Returns:
        Best matching item dict, or None if no items loaded.
    """
    if not _loaded:
        load_content_audit()

    if not _items:
        return None

    exclude_set = set(exclude_ids or [])
    candidates = [i for i in _items if i.get("id") not in exclude_set]
    if not candidates:
        candidates = list(_items)

    scored = [(item, _score_item(item, keywords, audience)) for item in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)

    best_item, best_score = scored[0]
    if best_score <= 0:
        return None
    return best_item


def match_content_for_collateral(
    step_description: str,
    industry: str = "",
    intent_topic: str = "",
    exclude_ids: Optional[List[int]] = None,
) -> Optional[Dict[str, Any]]:
    """Match a content audit item for the marketing collateral field in recommended sales program.

    Maps each recommendation step to appropriate keywords for matching.
    """
    keywords = []
    step_lower = step_description.lower()

    if "awareness" in step_lower or "credibility" in step_lower:
        keywords = ["thought leadership", industry, intent_topic]
    elif "challenge" in step_lower or "frame" in step_lower:
        keywords = ["case study", "insights", industry, intent_topic]
    elif "proven" in step_lower or "outcomes" in step_lower or "demonstrate" in step_lower:
        keywords = ["customer success", "case study", industry]
    elif "decision" in step_lower or "enable" in step_lower or "roi" in step_lower:
        keywords = ["ROI", "deployment", "solution brief", industry]
    else:
        keywords = [intent_topic, industry, step_description]

    # Filter empty keywords
    keywords = [k for k in keywords if k]

    return match_content(keywords=keywords, audience="ITDM", exclude_ids=exclude_ids)


def match_content_for_supporting_asset(
    persona: str,
    industry: str = "",
    priority_area: str = "",
    exclude_ids: Optional[List[int]] = None,
) -> Optional[Dict[str, Any]]:
    """Match a content audit item for the [Insert link to supporting asset] placeholder.

    Selects content appropriate for the persona and their priority area.
    """
    # Map personas to likely audience and relevant keywords
    audience = "ITDM"
    keywords = [priority_area, industry]

    persona_upper = persona.upper()
    if persona_upper in ("CFO",):
        audience = "BDM"
        keywords.extend(["ROI", "cost", "efficiency"])
    elif persona_upper in ("CIO",):
        keywords.extend(["IT", "modernization", "fleet management", "digital transformation"])
    elif persona_upper in ("CTO",):
        keywords.extend(["AI", "workstation", "technology", "infrastructure"])
    elif persona_upper in ("CISO",):
        keywords.extend(["security", "zero trust", "endpoint", "resilience"])
    elif persona_upper in ("COO",):
        audience = "BDM"
        keywords.extend(["operations", "productivity", "workforce", "hybrid work"])
    elif persona_upper in ("CPO", "CEO"):
        audience = "BDM"
        keywords.extend(["strategy", "workforce", "future of work"])

    keywords = [k for k in keywords if k]

    return match_content(keywords=keywords, audience=audience, exclude_ids=exclude_ids)
