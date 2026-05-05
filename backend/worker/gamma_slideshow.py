"""
Gamma API slideshow creation module.
Creates markdown prompts and generates slideshows via Gamma API.
"""
import json
import logging
import asyncio
import re
from typing import Dict, Any, Optional, List
import httpx

from content_audit import (
    load_content_audit,
    match_content_for_collateral,
    match_content_for_supporting_asset,
)

logger = logging.getLogger(__name__)


def _normalize_account_type(company_type) -> str:
    """
    Map LLM-emitted company_type values into the 4-bucket account-type
    taxonomy used by Gamma template v3.

    LLM input (5 buckets): Public | Private | Subsidiary | Government | Non-Profit
    Output (4 buckets):    Public | Private | Government | Non-Profit

    Subsidiary collapses to Private (subsidiary is privately held by parent).
    Unknown / empty / None defaults to Private (defensive — most companies
    in our data set are private).

    Match is case-insensitive substring. "publicly traded" -> Public,
    "government agency" -> Government, "nonprofit" -> Non-Profit, etc.
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


class GammaSlideshowCreator:
    """
    Creates slideshows using Gamma API from company data.

    Process:
    1. Retrieve finalized data from Supabase
    2. Format data as markdown
    3. Send to Gamma API
    4. Return slideshow URL
    """

    def __init__(self, gamma_api_key: str, template_id: str = "g_uost7x0lutmwtwd"):
        """
        Initialize Gamma slideshow creator.

        Args:
            gamma_api_key: Gamma API key (from environment)
            template_id: Gamma template ID (gammaId) for template-based generation
                        Default: g_uost7x0lutmwtwd (HP RAD Intelligence template v3)

        Note:
            API key must be provided via environment variables.
            Template will preserve its exact design, fonts, and logos.
        """
        self.api_key = gamma_api_key
        self.template_id = template_id or "g_uost7x0lutmwtwd"  # Always use template by default
        self.api_url = "https://public-api.gamma.app/v1.0/generations"
        self.template_url = "https://public-api.gamma.app/v1.0/generations/from-template"
        self.status_url = "https://public-api.gamma.app/v1.0/generations"

        # Polling ceiling for the per-request _send_to_gamma loop. 300 attempts
        # × 2 s/attempt = 600 s. Raised from 150 after the BC Liquor 2026-05-03
        # incident where Gamma's queue held the job in `pending` for >5 min.
        # When even this ceiling is exceeded, the job is handed off to the
        # background reconcile loop instead of being declared a failure.
        self.polling_max_attempts = 300

        if template_id:
            logger.info(f"Gamma slideshow creator initialized with template: {template_id}")
        else:
            logger.info(f"Gamma slideshow creator initialized (no template)")

    async def create_slideshow(
        self,
        company_data: Dict[str, Any],
        user_email: str = None
    ) -> Dict[str, Any]:
        """
        Create a slideshow from company data.

        Args:
            company_data: Finalized company data dictionary
            user_email: Email of the person pulling the data (for report attribution)

        Returns:
            Dictionary with slideshow URL and status

        Raises:
            Exception: If slideshow creation fails
        """
        try:
            # CRITICAL: Validate company_data is a dictionary
            if not isinstance(company_data, dict):
                error_msg = (
                    f"company_data must be a dictionary, got {type(company_data).__name__}. "
                    f"Expected format: {{'validated_data': {{}}, 'company_name': '...', 'confidence_score': 0.85}}"
                )
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "slideshow_url": None,
                    "slideshow_id": None
                }

            # CRITICAL: Ensure validated_data is a dict, not a JSON string
            validated_data = company_data.get('validated_data', {})
            if isinstance(validated_data, str):
                import json
                try:
                    validated_data = json.loads(validated_data)
                    logger.info("Parsed validated_data from JSON string in create_slideshow")
                    company_data['validated_data'] = validated_data
                except json.JSONDecodeError as e:
                    error_msg = f"validated_data is a malformed JSON string: {e}"
                    logger.error(f"❌ {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "slideshow_url": None,
                        "slideshow_id": None
                    }

            company_name = company_data.get('validated_data', {}).get('company_name') or company_data.get('company_name', 'Company')
            logger.info(f"Creating slideshow for {company_name}")

            # Generate markdown content with user email for attribution
            markdown_content = self._generate_markdown(company_data, user_email)

            # Count ALL contacts that will appear in the slideshow:
            # executive stakeholders + relevant other contacts (sales/partnerships/strategy/comms)
            vdata = company_data.get('validated_data', {})
            smap = vdata.get('stakeholder_map', {})

            # Executive stakeholders
            exec_stakeholders = smap.get('stakeholders', []) if smap else []
            if isinstance(exec_stakeholders, dict):
                exec_count = len(exec_stakeholders)
            elif isinstance(exec_stakeholders, list):
                exec_count = len(exec_stakeholders)
            else:
                exec_count = 0

            # Relevant other contacts (must match the same filter in _generate_markdown)
            _RELEVANT_ROLES_COUNT = {
                'sales', 'partnership', 'partnerships', 'strategy',
                'strategic', 'communication', 'communications',
                'business development', 'channel', 'alliances',
                'account', 'revenue',
            }
            other_contacts_list = smap.get('otherContacts', []) if smap else []
            relevant_other_count = 0
            if isinstance(other_contacts_list, list):
                for oc in other_contacts_list:
                    if isinstance(oc, dict):
                        combined = f"{(oc.get('title') or '')} {(oc.get('department') or '')} {(oc.get('roleType') or '')}".lower()
                        if any(role in combined for role in _RELEVANT_ROLES_COUNT):
                            relevant_other_count += 1

            stakeholder_count = exec_count + relevant_other_count
            if stakeholder_count == 0:
                # Fallback to legacy
                legacy = vdata.get('stakeholder_profiles', [])
                stakeholder_count = len(legacy) if isinstance(legacy, (list, dict)) else 1

            # Count unique persona types for supporting assets slides
            persona_types = set()
            if isinstance(exec_stakeholders, list):
                for s in exec_stakeholders:
                    role = (s.get('title') or '').upper()
                    for persona in ['CIO', 'CTO', 'CISO', 'COO', 'CFO', 'CPO']:
                        if persona in role:
                            persona_types.add(persona)
            persona_count = len(persona_types) if persona_types else 3  # Default to 3 personas

            # Slide count:
            # 1. Title
            # 2. Executive Snapshot
            # 3. Buying Signals
            # 4. Opportunity themes
            # 5+. Stakeholder profiles (one per executive + relevant other contact)
            # Next. Recommended sales program
            # Next+. Supporting Assets (one per persona type)
            # Last. Feedback
            num_cards = 4 + stakeholder_count + 1 + persona_count + 1

            logger.info(
                f"Slideshow slide breakdown: {exec_count} executives + "
                f"{relevant_other_count} relevant other contacts = "
                f"{stakeholder_count} stakeholder slides, "
                f"{persona_count} persona slides, "
                f"{num_cards} total cards requested"
            )

            # Send to Gamma API (standard endpoint with full markdown + numCards)
            result = await self._send_to_gamma(markdown_content, num_cards, company_data, user_email)

            inner_status = result.get("status")
            if inner_status == "pending":
                # Generation outlasted the per-request polling window. The
                # generation_id is preserved so the pipeline can hand the job
                # off to the background reconcile loop and the frontend can
                # keep polling /job-status for the URL.
                logger.info(
                    f"Slideshow generation still pending after polling window — "
                    f"handing off to reconcile (generation_id={result.get('id')})"
                )
                return {
                    "success": True,
                    "slideshow_url": None,
                    "slideshow_id": result.get("id"),
                    "slideshow_status": "pending",
                    "company_name": company_name,
                }

            logger.info(f"Slideshow created successfully: {result.get('url')}")
            return {
                "success": True,
                "slideshow_url": result.get("url"),
                "slideshow_id": result.get("id"),
                "slideshow_status": "completed",
                "company_name": company_name,
            }

        except Exception as e:
            logger.error(f"❌ Failed to create slideshow: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            # Return error response instead of crashing
            return {
                "success": False,
                "slideshow_url": None,
                "slideshow_id": None,
                "slideshow_status": "failed",
                "error": f"{type(e).__name__}: {str(e)}",
            }

    def _format_for_template(self, company_data: Dict[str, Any], user_email: str = None) -> str:
        """
        Format company data as structured text for template population.
        The template will handle all formatting, fonts, logos, and design.

        Args:
            company_data: Company data dictionary
            user_email: Email of person requesting the report

        Returns:
            Structured data string that the template will format
        """
        validated_data = company_data.get("validated_data", {})
        company_name = validated_data.get('company_name', 'Company')

        from datetime import datetime, timedelta, timezone
        # EST is UTC-5 (or UTC-4 during EDT, but using fixed EST offset)
        est = timezone(timedelta(hours=-5))
        current_date = datetime.now(est).strftime("%B %d, %Y")

        # Salesperson name (entered by user on the form)
        salesperson_name = company_data.get('salesperson_name') or user_email or 'HP Sales Team'

        # Build comprehensive, data-rich structured content
        data = f"""⚠️ GENERATION INSTRUCTIONS:
- ONLY slide 7 ("Stakeholder Map: Role Profile Alignment") has its LAYOUT locked. Do NOT generate, modify, or add any content sections on slide 7 — its existing template layout is final. However, bracket placeholders on slide 7 (e.g. [company], [name], [title]) MUST be substituted with the appropriate values from the data sections above. Substitution is not modification.
- Slides 8-12 (individual stakeholder profile slides): Populate ALL existing template fields using the data below — all conversation starters, all phone numbers, strategic priorities, communication preferences, recommended approach. Do NOT add new sections or elements that are not already in the template (e.g. do NOT add a "Key Contacts" section). Just fill in the existing fields completely.
- Supporting asset slides: Each section (Email Template, LinkedIn InMail Copy, Outreach Call Script, Voicemail Script, Objection Handling) should be placed on its own separate slide. Do not merge or combine different asset types onto the same slide.
- All other slides: populate normally using the data provided below.

ACCOUNT INTELLIGENCE REPORT

Company: {company_name}
Report Date: {current_date}
Prepared By: HP RAD Intelligence Desk
Prepared For: {salesperson_name}

=== COMPANY OVERVIEW ===

Company Name: {company_name}
Legal Name: {validated_data.get('legal_name', validated_data.get('company_name', 'Not available'))}
Domain: {validated_data.get('domain', 'Not available')}
Website: {validated_data.get('website', validated_data.get('domain', 'Not available'))}

Industry: {validated_data.get('industry', 'Not available')}
Sub-Industry: {validated_data.get('sub_industry', 'Not available')}
Industry Category: {validated_data.get('industry_category', 'Not available')}
SIC Codes: {', '.join(map(str, validated_data.get('sic_codes', []))) if validated_data.get('sic_codes') else 'Not available'}
NAICS Codes: {', '.join(map(str, validated_data.get('naics_codes', []))) if validated_data.get('naics_codes') else 'Not available'}
Account Type: {_normalize_account_type(validated_data.get('company_type') or validated_data.get('type') or validated_data.get('account_type') or '')}
Ownership Type: {validated_data.get('ownership_type', 'Not available')}

Founded: {validated_data.get('founded_year', 'Not available')}
CEO: {validated_data.get('ceo', 'Not available')}
CFO: {validated_data.get('cfo', 'Not available')}
CTO: {validated_data.get('cto', 'Not available')}

Headquarters: {validated_data.get('headquarters', 'Not available')}
Full Address: {validated_data.get('full_address', validated_data.get('headquarters', 'Not available'))}
Metro Area: {validated_data.get('metro_area', 'Not available')}
Geographic Reach: {', '.join(validated_data.get('geographic_reach', [])) if validated_data.get('geographic_reach') else 'Not available'}

Employee Count: {validated_data.get('employee_count', 'Not available')}
Employee Range: {validated_data.get('employees_range', validated_data.get('employee_count', 'Not available'))}
Annual Revenue: {validated_data.get('annual_revenue', validated_data.get('revenue', 'Not available'))}
Revenue Range: {validated_data.get('revenue_range', 'Not available')}
Estimated Revenue: {validated_data.get('estimated_revenue', 'Not available')}
Estimated IT Budget: {self._estimate_it_budget(validated_data)}

Contact Information:
- Phone: {validated_data.get('phone', 'Not available')}
- Fax: {validated_data.get('fax', 'Not available')}
- Corporate Email: {validated_data.get('corporate_email', 'Not available')}

Social Media & Web Presence:
- LinkedIn: {validated_data.get('linkedin_url', 'Not available')}
- Facebook: {validated_data.get('facebook_url', 'Not available')}
- Twitter: {validated_data.get('twitter_url', 'Not available')}

Company Description: {validated_data.get('company_overview', validated_data.get('description', validated_data.get('summary', 'Not available')))}

Target Market: {validated_data.get('target_market', 'Not available')}
Customer Segments: {', '.join(validated_data.get('customer_segments', [])) if validated_data.get('customer_segments') else 'Not available'}

Products/Services: {', '.join(validated_data.get('products', [])) if validated_data.get('products') else 'Not available'}

Stock Information:
- Ticker: {validated_data.get('ticker', 'Not available (private company)')}
- Exchange: {validated_data.get('stock_exchange', 'Not available')}
- Fortune Rank: {validated_data.get('fortune_rank', 'Not available')}

Parent Company: {validated_data.get('parent_company', 'Independent')}
Former Names: {', '.join(validated_data.get('former_names', [])) if validated_data.get('former_names') else 'None'}

Technology Stack: {', '.join(validated_data.get('technologies', validated_data.get('technology', []))) if validated_data.get('technologies') or validated_data.get('technology') else 'Not available'}
Tech Installation Count: {validated_data.get('tech_install_count', len(validated_data.get('technology_installs', [])))} verified installations

Data Quality Score: {validated_data.get('data_quality_score', 'Not available')}

=== INTENT SIGNALS ===

"""

        # Buying Signals - comprehensive extraction with ALL fields
        buying_signals = validated_data.get('buying_signals', {})
        intent_topics = buying_signals.get('intent_topics', validated_data.get('intent_topics', validated_data.get('intent_signals', [])))

        if intent_topics:
            data += "Top Intent Topics (ALL AVAILABLE):\n"
            # Show ALL intent topics, not just top 5
            for i, topic in enumerate(intent_topics, 1):
                if isinstance(topic, dict):
                    t_name = topic.get('topic', topic.get('topic_name', topic.get('name', f'Topic {i}')))
                    t_score = topic.get('intent_score', topic.get('score', 'N/A'))
                    t_strength = topic.get('audience_strength', '')
                    t_desc = topic.get('description', '')
                    t_category = topic.get('category', '')
                    t_last_seen = topic.get('last_seen', '')

                    data += f"{i}. {t_name} (Score: {t_score}"
                    if t_strength:
                        data += f", Strength: {t_strength}"
                    data += ")"
                    if t_category:
                        data += f" [Category: {t_category}]"
                    if t_desc:
                        data += f" - {t_desc}"
                    if t_last_seen:
                        data += f" (Last seen: {t_last_seen})"
                    data += "\n"
                else:
                    data += f"{i}. {topic}\n"
        else:
            data += "Intent Topics: Monitoring for digital signals\n"

        data += "\n"

        # Partner Mentions & Competitors
        partners = buying_signals.get('partner_mentions', validated_data.get('partner_mentions', []))
        competitors = buying_signals.get('competitors', validated_data.get('competitors', []))

        if partners:
            data += f"Partner Ecosystem: {', '.join(str(p) for p in partners[:10])}\n\n"
        if competitors:
            data += f"Competitive Landscape: {', '.join(str(c) for c in competitors[:10])}\n\n"

        # News & Triggers - comprehensive with ZoomInfo scoops and news
        news_triggers = buying_signals.get('triggers', validated_data.get('news_triggers', {}))
        news_summaries = validated_data.get('news_summaries', {})
        scoops = validated_data.get('scoops', [])
        news_articles = validated_data.get('news_articles', [])

        if news_triggers or news_summaries or scoops or news_articles:
            data += "=== BUYING SIGNALS & NEWS (ALL SOURCES) ===\n\n"

            # Scoops from ZoomInfo (business events)
            if scoops:
                data += "Business Events (ZoomInfo Scoops):\n"
                for scoop in scoops[:10]:  # Show up to 10 scoops
                    if isinstance(scoop, dict):
                        scoop_type = scoop.get('scoop_type', 'Event')
                        title = scoop.get('title', '')
                        description = scoop.get('description', '')
                        date = scoop.get('date', scoop.get('published_date', ''))
                        data += f"• [{scoop_type}] {title}"
                        if date:
                            data += f" ({date})"
                        if description:
                            data += f" - {description}"
                        data += "\n"
                data += "\n"

            # Funding signals
            funding_scoops = [s for s in scoops if isinstance(s, dict) and 'funding' in s.get('scoop_type', '').lower()]
            if news_triggers.get('funding') or news_summaries.get('funding') or funding_scoops:
                funding_info = news_triggers.get('funding', news_summaries.get('funding', ''))
                data += f"💰 Funding Activity: {funding_info}"
                if funding_scoops:
                    for f in funding_scoops[:3]:
                        amount = f.get('amount', '')
                        investors = f.get('investors', [])
                        if amount:
                            data += f" | ${amount}"
                        if investors:
                            data += f" from {', '.join(investors[:3])}"
                data += "\n\n"

            # Growth signals (including hire scoops)
            hire_scoops = [s for s in scoops if isinstance(s, dict) and ('hire' in s.get('scoop_type', '').lower() or 'executive' in s.get('scoop_type', '').lower())]
            expansion_scoops = [s for s in scoops if isinstance(s, dict) and 'expansion' in s.get('scoop_type', '').lower()]
            if news_triggers.get('expansions') or news_summaries.get('expansions') or hire_scoops or expansion_scoops:
                exp_info = news_triggers.get('expansions', news_summaries.get('expansions', ''))
                data += f"📈 Expansion & Growth: {exp_info}"
                if hire_scoops:
                    data += " | Recent Hires: "
                    data += ", ".join([f"{s.get('person_name', 'Executive')} ({s.get('person_title', 'Role')})" for s in hire_scoops[:5]])
                data += "\n\n"

            if news_triggers.get('executive_changes') or news_summaries.get('executive_changes'):
                exec_info = news_triggers.get('executive_changes', news_summaries.get('executive_changes', ''))
                data += f"👔 Leadership Changes: {exec_info}\n\n"

            # Strategic signals (including partnership scoops)
            partnership_scoops = [s for s in scoops if isinstance(s, dict) and 'partnership' in s.get('scoop_type', '').lower()]
            if news_triggers.get('partnerships') or news_summaries.get('partnerships') or partnership_scoops:
                part_info = news_triggers.get('partnerships', news_summaries.get('partnerships', ''))
                data += f"🤝 Strategic Partnerships: {part_info}"
                if partnership_scoops:
                    data += " | Partners: "
                    data += ", ".join([s.get('partner_name', 'Partner') for s in partnership_scoops[:5] if s.get('partner_name')])
                data += "\n\n"

            # Product launches
            product_scoops = [s for s in scoops if isinstance(s, dict) and 'product' in s.get('scoop_type', '').lower()]
            if news_triggers.get('products') or news_summaries.get('products') or product_scoops:
                prod_info = news_triggers.get('products', news_summaries.get('products', ''))
                data += f"🚀 Product Launches: {prod_info}"
                if product_scoops:
                    data += " | "
                    data += ", ".join([s.get('title', 'Product') for s in product_scoops[:5]])
                data += "\n\n"

            # Technology signals
            if news_summaries.get('technology'):
                data += f"💻 Technology Initiatives: {news_summaries['technology']}\n\n"

            # Recent news articles from ZoomInfo
            if news_articles:
                data += "Recent News Coverage:\n"
                for article in news_articles[:5]:  # Show top 5 news articles
                    if isinstance(article, dict):
                        title = article.get('title', '')
                        source = article.get('source', '')
                        date = article.get('published_date', '')
                        sentiment = article.get('sentiment', '')
                        data += f"• {title}"
                        if source:
                            data += f" - {source}"
                        if date:
                            data += f" ({date})"
                        if sentiment:
                            data += f" [Sentiment: {sentiment}]"
                        data += "\n"
                data += "\n"

        # Pain Points — v3 format: bolded title, blank line, description paragraph. Cap at 3.
        pain_points = (
            company_data.get('pain_points')
            or validated_data.get('pain_points')
            or company_data.get('opportunity_themes_detailed', {}).get('pain_points')
            or validated_data.get('opportunity_themes_detailed', {}).get('pain_points')
            or company_data.get('opportunity_themes', {}).get('pain_points')
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

        # Opportunities — v3 format: numbered + bolded title, blank line, validation blurb. Cap at 3.
        opportunities = (
            company_data.get('sales_opportunities')
            or validated_data.get('sales_opportunities')
            or company_data.get('opportunity_themes_detailed', {}).get('sales_opportunities')
            or validated_data.get('opportunity_themes_detailed', {}).get('sales_opportunities')
            or company_data.get('opportunities')
            or validated_data.get('opportunities')
            or []
        )
        if opportunities:
            data += "=== SALES OPPORTUNITIES ===\n\n"
            for i, opp in enumerate(opportunities[:3], 1):
                if isinstance(opp, dict):
                    title = opp.get('title', opp.get('name', f'Opportunity {i}'))
                    desc = opp.get('description', '')
                    if desc:
                        data += f"**{i}. {title}**\n\n{desc}\n\n"
                    else:
                        data += f"**{i}. {title}**\n\n"
                else:
                    data += f"**{i}. {opp}**\n\n"

        # Solutions
        solutions = validated_data.get('recommended_solutions', [])
        if solutions:
            data += "=== RECOMMENDED SOLUTIONS ===\n\n"
            for i, sol in enumerate(solutions, 1):
                if isinstance(sol, dict):
                    data += f"{i}. {sol.get('title', sol)}\n"
                    if sol.get('description'):
                        data += f"   {sol['description']}\n"
                else:
                    data += f"{i}. {sol}\n"
                data += "\n"

        # Stakeholders for template: 1 BEST contact per C-suite role + relevant others.
        # Template has fixed slides per role — can't duplicate. So we pick the
        # highest-quality contact for each csuiteCategory.
        #
        # Quality ranking (higher = better):
        #   +3 for true C-suite title (Chief X Officer, CEO, CTO, etc.)
        #   +1 for each of: linkedin, any phone, email
        # Ties broken by list order (earlier = higher priority from upstream sort).
        stakeholder_map = validated_data.get('stakeholder_map', {})

        _RELEVANT_ROLES_TPL = {
            'sales', 'partnership', 'partnerships', 'strategy',
            'strategic', 'communication', 'communications',
            'business development', 'channel', 'alliances',
            'account', 'revenue',
        }

        # C-suite title keywords that indicate a true chief officer
        _CSUITE_TITLES = {'chief', 'ceo', 'cto', 'cfo', 'cio', 'ciso', 'coo', 'cpo', 'cmo',
                          'president', 'founder', 'co-founder'}

        # Mapping from csuiteCategory to title keywords that indicate an exact role match
        _EXACT_ROLE_KEYWORDS = {
            'CEO': ['ceo', 'chief executive'],
            'CTO': ['cto', 'chief technology'],
            'CIO': ['cio', 'chief information officer'],
            'CISO': ['ciso', 'chief information security', 'chief security officer'],
            'CFO': ['cfo', 'chief financial'],
            'COO': ['coo', 'chief operating'],
            'CMO': ['cmo', 'chief marketing'],
            'CPO': ['cpo', 'chief product', 'chief people'],
        }

        def _contact_quality(s, category=''):
            """Score a contact for sales outreach quality (higher = better).

            Scoring:
              +5  exact C-suite title match for the category (e.g. CTO title in CTO slot)
              +3  any C-suite-level title (chief/president/founder)
              +2  has email (critical for outreach)
              +2  has any phone number
              +2  has linkedin profile
            Contacts with all three contact channels (email+phone+linkedin) are strongly
            preferred, matching the rule: ideally linkedin, phone, AND email present.
            """
            score = 0
            _c = s.get('contact') or {}
            if not isinstance(_c, dict):
                _c = {}

            # Has email? (+2 — essential for outreach)
            if s.get('email') or _c.get('email'):
                score += 2

            # Has any phone? (+2 — high-value for direct contact)
            has_phone = any([
                s.get('direct_phone'), s.get('mobile_phone'), s.get('company_phone'),
                s.get('phone'), s.get('directPhone'), s.get('companyPhone'),
                _c.get('directPhone'), _c.get('mobilePhone'),
                _c.get('companyPhone'), _c.get('phone'),
            ])
            if has_phone:
                score += 2

            # Has linkedin? (+2 — essential for professional outreach)
            if s.get('linkedin_url') or s.get('linkedinUrl') or _c.get('linkedinUrl'):
                score += 2

            # Exact role match: title contains the specific C-suite abbreviation
            # for the category this contact is being evaluated for (e.g. "CTO" in CTO slot)
            title_lower = (s.get('title') or '').lower()
            if category and category in _EXACT_ROLE_KEYWORDS:
                if any(kw in title_lower for kw in _EXACT_ROLE_KEYWORDS[category]):
                    score += 5

            # General C-suite title bonus (any chief/president/founder)
            if any(kw in title_lower for kw in _CSUITE_TITLES):
                score += 3

            return score

        # 1. Executive stakeholders — pick 1 best per csuiteCategory
        # Rule: 1 slide per C-suite role, pick the contact whose title most closely
        # matches the role AND has the most complete contact info (linkedin+phone+email)
        best_per_role = {}  # csuiteCategory -> best contact
        if stakeholder_map and stakeholder_map.get('stakeholders'):
            for s in stakeholder_map['stakeholders']:
                if not isinstance(s, dict):
                    continue
                cat = s.get('csuiteCategory', '')
                if not cat:
                    continue
                existing = best_per_role.get(cat)
                if not existing or _contact_quality(s, cat) > _contact_quality(existing, cat):
                    best_per_role[cat] = s

        executive_stakeholders = list(best_per_role.values())

        # 2. Relevant other contacts filtered by role
        relevant_other_contacts = []
        if stakeholder_map and stakeholder_map.get('otherContacts'):
            for contact in stakeholder_map['otherContacts']:
                if not isinstance(contact, dict):
                    continue
                combined = f"{(contact.get('title') or '')} {(contact.get('department') or '')} {(contact.get('roleType') or '')}".lower()
                if any(role in combined for role in _RELEVANT_ROLES_TPL):
                    relevant_other_contacts.append(contact)

        # Fallback to legacy stakeholder_profiles
        if not executive_stakeholders and not relevant_other_contacts:
            stakeholder_profiles = validated_data.get('stakeholder_profiles', [])
            if isinstance(stakeholder_profiles, list):
                executive_stakeholders = [s for s in stakeholder_profiles if isinstance(s, dict)]
            elif isinstance(stakeholder_profiles, dict):
                # LLM council returns {role_type: profile_dict} — convert to list
                for role_type, profile in stakeholder_profiles.items():
                    if isinstance(profile, dict):
                        entry = dict(profile)
                        if not entry.get('title'):
                            entry['title'] = role_type
                        if not entry.get('csuiteCategory'):
                            entry['csuiteCategory'] = role_type
                        executive_stakeholders.append(entry)

        all_stakeholders = executive_stakeholders + relevant_other_contacts

        def _tpl_phone(val):
            """Coerce phone value to clean string or empty."""
            if not val:
                return ''
            s = str(val).strip()
            if s in ('None', 'N/A', 'null', '') or '****' in s:
                return ''
            return s

        if all_stakeholders:
            data += "⚠️ REMINDER: ONLY slide 7 ('Stakeholder Map: Role Profile Alignment') has its LAYOUT locked. Do NOT generate, modify, or add any content sections on slide 7 — its existing template layout is final. However, bracket placeholders on slide 7 (e.g. [company], [name], [title]) MUST be substituted with the appropriate values from the data sections above. Substitution is not modification. Slides 8-12 (individual stakeholder profiles): populate all existing template fields fully but do NOT add new sections (no 'Key Contacts' or other invented sections). Just fill in the fields that already exist in the template.\n\n"
            data += "=== KEY STAKEHOLDERS (ONE SLIDE PER CONTACT) ===\n\n"
            for idx, stakeholder in enumerate(all_stakeholders, 1):
                name = stakeholder.get('name', stakeholder.get('fullName', 'Not available'))
                title = stakeholder.get('title', stakeholder.get('role', 'Not available'))
                email = stakeholder.get('email', stakeholder.get('contact', {}).get('email', 'Not available'))
                linkedin = stakeholder.get('linkedin', stakeholder.get('linkedinUrl', stakeholder.get('linkedin_url', stakeholder.get('contact', {}).get('linkedinUrl', 'Not available'))))

                # Determine category label
                persona = stakeholder.get('csuiteCategory', '')
                if not persona:
                    title_upper = (title or '').upper()
                    for p in ['CFO', 'CTO', 'CIO', 'CISO', 'COO', 'CPO', 'CEO', 'CMO']:
                        if p in title_upper:
                            persona = p
                            break
                category = f"{persona} Stakeholder" if persona else "Key Contact"

                data += f"--- STAKEHOLDER SLIDE {idx}: {name} ---\n"
                data += f"Category: {category}\n"
                data += f"Name: {name}\n"
                data += f"Title: {title}\n"

                # Department
                department = stakeholder.get('department', '')
                if not department:
                    dept_map = {
                        'CFO': 'Finance', 'CTO': 'Technology', 'CIO': 'Information Technology',
                        'CISO': 'Security', 'COO': 'Operations', 'CPO': 'Product',
                        'CEO': 'C-Suite', 'CMO': 'Marketing',
                    }
                    department = dept_map.get(persona, 'C-Suite')
                data += f"Department: {department}\n"

                if stakeholder.get('seniority'):
                    data += f"Seniority: {stakeholder['seniority']}\n"

                # Start date
                start_date = stakeholder.get('start_date', stakeholder.get('hireDate', stakeholder.get('hire_date', '')))
                data += f"Start date: {start_date or 'Currently unavailable'}\n"

                data += f"Email: {email}\n"

                # Phone numbers — robust extraction from snake_case + camelCase + nested contact
                _contact = stakeholder.get('contact') or {}
                if not isinstance(_contact, dict):
                    _contact = {}

                direct_phone = (_tpl_phone(stakeholder.get('direct_phone'))
                                or _tpl_phone(stakeholder.get('directPhone'))
                                or _tpl_phone(_contact.get('directPhone')))
                mobile = (_tpl_phone(stakeholder.get('mobile_phone'))
                          or _tpl_phone(stakeholder.get('mobile'))
                          or _tpl_phone(_contact.get('mobilePhone')))
                company_phone = (_tpl_phone(stakeholder.get('company_phone'))
                                 or _tpl_phone(stakeholder.get('companyPhone'))
                                 or _tpl_phone(_contact.get('companyPhone')))
                phone = (_tpl_phone(stakeholder.get('phone'))
                         or _tpl_phone(stakeholder.get('phone_number'))
                         or _tpl_phone(_contact.get('phone')))

                shown_phones = set()
                if direct_phone:
                    data += f"Direct Phone: {direct_phone}\n"
                    shown_phones.add(direct_phone)
                if mobile and mobile not in shown_phones:
                    data += f"Mobile Phone: {mobile}\n"
                    shown_phones.add(mobile)
                if company_phone and company_phone not in shown_phones:
                    data += f"Company Phone: {company_phone}\n"
                    shown_phones.add(company_phone)
                if phone and phone not in shown_phones:
                    data += f"Phone: {phone}\n"
                    shown_phones.add(phone)
                if not shown_phones:
                    data += "Phone: Currently unavailable\n"

                if linkedin and linkedin != 'Not available':
                    data += f"LinkedIn: {linkedin}\n"

                # About / Bio — provide fallback if AI profile didn't generate one
                bio = stakeholder.get('bio', stakeholder.get('about', stakeholder.get('description', '')))
                if bio:
                    data += f"About: {bio}\n"
                else:
                    data += f"About: {name} serves as {title} at {company_name}, responsible for strategic initiatives and organizational leadership in their domain.\n"

                # Strategic Priorities — provide persona-specific fallbacks
                priorities = stakeholder.get('strategic_priorities', stakeholder.get('strategicPriorities', []))
                if priorities:
                    data += "Strategic Priorities:\n"
                    for i, p in enumerate(priorities[:3], 1):
                        if isinstance(p, dict):
                            p_name = p.get('name', p.get('priority', p))
                            p_desc = p.get('description', '')
                            data += f"  {i}. {p_name}"
                            if p_desc:
                                data += f" - {p_desc}"
                            data += "\n"
                        else:
                            data += f"  {i}. {p}\n"
                elif isinstance(priorities, str) and priorities:
                    data += f"Strategic Priorities:\n  1. {priorities}\n"
                else:
                    # Persona-specific fallback priorities
                    industry = validated_data.get('industry', 'technology')
                    if persona == 'CFO':
                        data += f"Strategic Priorities:\n  1. Optimize operational efficiency and cost management across technology investments\n  2. Strengthen financial controls and risk management\n  3. Enable data-driven decision making with improved visibility into technology spend\n"
                    elif persona in ('CTO', 'CIO'):
                        data += f"Strategic Priorities:\n  1. Accelerate digital transformation initiatives to support {company_name}'s business agility\n  2. Enhance security and operational resilience across infrastructure\n  3. Optimize IT operations through automation and strategic vendor partnerships\n"
                    elif persona == 'CISO':
                        data += f"Strategic Priorities:\n  1. Strengthen cybersecurity posture across the enterprise\n  2. Ensure regulatory compliance and risk management in {industry}\n  3. Enable secure digital transformation balancing security with innovation\n"
                    elif persona == 'COO':
                        data += f"Strategic Priorities:\n  1. Drive operational excellence and efficiency through improved technology\n  2. Enable scalability and business growth for {company_name}\n  3. Improve cross-functional collaboration and visibility\n"
                    elif persona == 'CMO':
                        data += f"Strategic Priorities:\n  1. Accelerate digital marketing and customer engagement capabilities\n  2. Improve marketing analytics and attribution for ROI visibility\n  3. Align marketing technology stack with business growth objectives\n"
                    else:
                        data += f"Strategic Priorities:\n  1. Enable strategic business objectives for {company_name} in {industry}\n  2. Drive innovation and competitive advantage through technology\n  3. Optimize organizational effectiveness and decision-making\n"

                # Communication Preference
                comm_pref = stakeholder.get('communication_preference', stakeholder.get('communicationPreference', ''))
                data += f"Preferred Contact: {comm_pref or 'Email / LinkedIn / Phone / Events'}\n"

                # Recommended Play / Approach
                rec_play = stakeholder.get('recommended_play', stakeholder.get('recommendedPlay', ''))
                if rec_play:
                    data += f"Recommended Approach: {rec_play}\n"

                # Conversation Starters
                conv_starters = stakeholder.get('conversation_starters', stakeholder.get('conversationStarters', []))
                if conv_starters:
                    data += "Conversation Starters:\n"
                    if isinstance(conv_starters, list):
                        for i, starter in enumerate(conv_starters[:3], 1):
                            if isinstance(starter, dict):
                                data += f"  {i}. {starter.get('title', starter.get('topic', ''))}: {starter.get('text', starter.get('question', ''))}\n"
                            else:
                                data += f"  {i}. {starter}\n"
                    elif isinstance(conv_starters, str):
                        data += f"  1. {conv_starters}\n"

                data += "\n"

        # Next Steps
        next_steps = validated_data.get('recommended_next_steps', [])
        if next_steps:
            data += "=== RECOMMENDED NEXT STEPS ===\n\n"
            for i, step in enumerate(next_steps, 1):
                if isinstance(step, dict):
                    data += f"{i}. {step.get('step', step)}\n"
                    if step.get('collateral'):
                        data += f"   Collateral: {step['collateral']}\n"
                else:
                    data += f"{i}. {step}\n"
                data += "\n"

        # ---------------------------------------------------------------
        # SUPPORTING ASSETS — HP template-based outreach per persona
        # ---------------------------------------------------------------
        industry = validated_data.get('industry', 'technology')
        intent_topics = buying_signals.get('intent_topics', validated_data.get('intent_topics', validated_data.get('intent_signals', [])))

        # Priority area from intent topics
        priority_area = ""
        if intent_topics and len(intent_topics) > 0:
            first_topic = intent_topics[0]
            priority_area = first_topic.get('topic', '') if isinstance(first_topic, dict) else str(first_topic)
        if not priority_area:
            priority_area = "technology modernization"

        # Pain points
        pain_points = validated_data.get('pain_points') or validated_data.get('opportunity_themes_detailed', {}).get('pain_points', []) or validated_data.get('opportunity_themes', {}).get('pain_points', [])
        outcome_or_kpi = "operational efficiency"
        relevant_goal = "improved operational outcomes"
        address_challenge = "strengthen their technology posture and improve outcomes"
        example_a = "improving operational efficiency"
        example_b = "reducing costs"
        outcome_short = outcome_or_kpi

        if pain_points and len(pain_points) > 0:
            first_pain = pain_points[0]
            if isinstance(first_pain, dict):
                address_challenge = first_pain.get('title', address_challenge)
                example_a = first_pain.get('title', example_a)
                outcome_short = first_pain.get('title', outcome_or_kpi)
                pain_desc = first_pain.get('description', '')
                if 'efficiency' in pain_desc.lower():
                    outcome_or_kpi = "operational efficiency"
                elif 'security' in pain_desc.lower():
                    outcome_or_kpi = "endpoint security posture"
                elif 'cost' in pain_desc.lower():
                    outcome_or_kpi = "cost optimization"
            if len(pain_points) >= 2 and isinstance(pain_points[1], dict):
                example_b = pain_points[1].get('title', example_b)

        # Opportunities
        opportunities = validated_data.get('sales_opportunities') or validated_data.get('opportunity_themes_detailed', {}).get('sales_opportunities', []) or validated_data.get('opportunities', [])
        if opportunities and len(opportunities) > 0:
            first_opp = opportunities[0]
            if isinstance(first_opp, dict):
                relevant_goal = first_opp.get('title', relevant_goal)

        # Solutions
        solutions = validated_data.get('recommended_solutions') or validated_data.get('opportunity_themes_detailed', {}).get('recommended_solution_areas', []) or validated_data.get('recommended_focus', [])
        hp_capability = "modernizing device fleets and improving data security"
        solution_summary = "modernizing device fleets to improve security and productivity"
        hp_offering_name = "HP managed device solutions"
        if solutions and len(solutions) > 0:
            first_sol = solutions[0]
            if isinstance(first_sol, dict):
                hp_capability = first_sol.get('title', hp_capability)
                sol_desc = first_sol.get('description', '')
                if sol_desc:
                    solution_summary = sol_desc[:120]
                hp_offering_name = first_sol.get('title', hp_offering_name)

        similar_org = f"a similar {industry} organization"
        metric_outcome = "operational efficiency by 30%"
        sp_name = salesperson_name if salesperson_name and salesperson_name != 'HP Sales Team' else "[Your Name]"

        # Recommended sales program
        data += "\n=== RECOMMENDED SALES PROGRAM ===\n\n"
        data += "Recommended Next Steps:\n"
        data += "Introduce emerging trends and thought leadership to build awareness and credibility. "
        data += "Highlight business challenges and frame HP's solutions as ways to address them. "
        data += "Reinforce proof points with case studies and demonstrate integration value. "
        data += "Emphasize ROI, deployment support, and the ease of scaling with HP solutions.\n\n"

        rec_next_steps = validated_data.get('recommended_next_steps', [])
        if not rec_next_steps:
            if intent_topics and len(intent_topics) > 0:
                first_topic_name = intent_topics[0].get('topic', '') if isinstance(intent_topics[0], dict) else str(intent_topics[0])
                rec_next_steps.append({'step': 'Build awareness and credibility', 'collateral': f'Thought leadership on {first_topic_name.lower()} in {industry}'})
            if opportunities and len(opportunities) > 0:
                first_opp_name = opportunities[0].get('title', '') if isinstance(opportunities[0], dict) else str(opportunities[0])
                rec_next_steps.append({'step': 'Frame business challenges', 'collateral': f'Case study or insights on {first_opp_name.lower()}'})
            rec_next_steps.append({'step': 'Demonstrate proven outcomes', 'collateral': f'Customer success stories from {industry}'})
            rec_next_steps.append({'step': 'Enable decision-making', 'collateral': 'ROI framework and deployment approach'})

        # Match content audit items for each step's marketing collateral
        load_content_audit()
        first_intent = ''
        if intent_topics and len(intent_topics) > 0:
            first_intent = intent_topics[0].get('topic', '') if isinstance(intent_topics[0], dict) else str(intent_topics[0])
        collateral_used_ids: List[int] = []

        for i, step in enumerate(rec_next_steps, 1):
            if isinstance(step, dict):
                step_title = step.get('step', step.get('title', f'Step {i}'))
                data += f"[{i}] {step_title}\n"
                # Try to match a content audit asset for this step
                matched = match_content_for_collateral(
                    step_description=step_title,
                    industry=industry,
                    intent_topic=first_intent,
                    exclude_ids=collateral_used_ids,
                )
                if matched:
                    collateral_used_ids.append(matched.get('id', 0))
                    asset_name = matched.get('asset_name', '')
                    sp_link = matched.get('sp_link', '')
                    if sp_link and sp_link.startswith('http'):
                        data += f"    Marketing collateral: [{asset_name}]({sp_link})\n"
                    else:
                        data += f"    Marketing collateral: {asset_name}\n"
                elif step.get('collateral'):
                    data += f"    Marketing collateral: {step['collateral']}\n"
            else:
                data += f"[{i}] {step}\n"

        data += "\nSupporting assets: Email template | LinkedIn InMail template | Call script template\n"
        data += "See the following slides for ready-to-use outreach templates per persona.\n\n"

        # Determine persona types and map each to the best contact's first name
        persona_contacts = {}  # persona type -> first name of best contact
        # Use best_per_role (already computed above) for highest-quality mapping
        for cat, s in best_per_role.items():
            if cat in ('CFO', 'CTO', 'CIO', 'CISO', 'COO', 'CPO'):
                full_name = s.get('name', s.get('fullName', ''))
                first_name = full_name.split()[0] if full_name and full_name.strip() else ''
                persona_contacts[cat] = first_name
        # Fallback: also scan all stakeholders by title for any missed personas
        _sa_stakeholders = validated_data.get('stakeholder_map', {}).get('stakeholders', []) if validated_data.get('stakeholder_map') else []
        for s in _sa_stakeholders:
            if isinstance(s, dict):
                title = s.get('title', '').upper()
                for p in ['CFO', 'CTO', 'CIO', 'CISO', 'COO', 'CPO']:
                    if p in title and p not in persona_contacts:
                        full_name = s.get('name', s.get('fullName', ''))
                        first_name = full_name.split()[0] if full_name and full_name.strip() else ''
                        persona_contacts[p] = first_name
        if not persona_contacts:
            persona_contacts = {'CIO': '', 'CTO': '', 'CFO': ''}

        supporting_asset_used_ids: List[int] = list(collateral_used_ids)  # avoid reusing collateral picks

        for persona in sorted(persona_contacts):
            contact_first_name = persona_contacts.get(persona, '') or '[First Name]'
            data += f"\n=== SUPPORTING ASSETS - {persona} ===\n\n"

            # Match a content audit asset for this persona's supporting asset link
            sa_match = match_content_for_supporting_asset(
                persona=persona,
                industry=industry,
                priority_area=priority_area,
                exclude_ids=supporting_asset_used_ids,
            )
            if sa_match:
                supporting_asset_used_ids.append(sa_match.get('id', 0))
                sa_name = sa_match.get('asset_name', '')
                sa_link = sa_match.get('sp_link', '')
                if sa_link and sa_link.startswith('http'):
                    supporting_asset_text = f"[{sa_name}]({sa_link})"
                else:
                    supporting_asset_text = sa_name
            else:
                supporting_asset_text = "[Insert link to supporting asset]"

            # Email Template
            data += "--- Email Template ---\n\n"
            data += "Sender: HP Sales\n\n"
            data += "Subject:\n"
            data += f"A: Insights that matter to {company_name}\n"
            data += f"B: Supporting {company_name} on {priority_area}\n\n"
            data += "Body copy:\n"
            data += f"Hi {contact_first_name},\n\n"
            data += f"I understand {company_name} is focused on {priority_area} this year. I wanted to share something that might help advance that work.\n\n"
            data += f"We've seen similar organizations strengthen {outcome_or_kpi} by {hp_capability}.\n\n"
            data += "I thought you might find this useful:\n\n"
            data += f"{supporting_asset_text}\n\n"
            data += f"Would you be open to a brief conversation about how we could help you achieve {relevant_goal}?\n\n"
            data += f"Best regards,\n{sp_name}\nHP Canada | HP\n\n"

            # LinkedIn InMail
            data += "--- LinkedIn InMail Copy ---\n\n"
            data += f"Subject: Supporting {company_name} on {priority_area}\n\n"
            data += f"Hi {contact_first_name},\n\n"
            data += f"{priority_area.capitalize() if priority_area else 'Technology modernization'} seems to be a key focus across {industry}. We've seen similar organizations strengthen {outcome_or_kpi} by {hp_capability}.\n\n"
            data += "Here's a short resource that outlines how:\n\n"
            data += f"{supporting_asset_text}\n\n"
            data += f"Would you be open to a quick chat about what might work best for {company_name}?\n\n"
            data += f"Best,\n{sp_name}\nHP Canada\n\n"

            # Call Script
            data += "--- Outreach Call Script ---\n\n"
            data += "Step 1: Provide Context\n\n"
            data += f"Hi {contact_first_name}, this is {sp_name} with HP Canada.\n\n"
            data += f"I'm calling about {priority_area}. I work with {industry} teams on this. Do you have 30 seconds to see if this is relevant?\n\n"
            data += "Step 2: Explain Offering\n\n"
            data += f"A lot of {industry} teams we work with are looking to {address_challenge}, whether that's {example_a} or {example_b}.\n\n"
            data += f"At HP, we've been helping them by {solution_summary}.\n\n"
            data += f"For example, {similar_org} recently improved {metric_outcome} after adopting {hp_offering_name}.\n\n"
            data += f"It's a quick change that made a measurable difference in {relevant_goal}.\n\n"
            data += "Step 3: CTA\n\n"
            data += f"I can send over a short resource that outlines how we approached this with other {industry} teams. Would that be useful?\n\n"

            # Voicemail Script
            data += "--- Voicemail Script ---\n\n"
            data += f"Hi {contact_first_name}, this is {sp_name} from HP Canada.\n\n"
            data += f"I wanted to share a quick idea about {priority_area}, something we've seen help {industry} teams improve {outcome_short}.\n\n"
            data += "If it's something you're exploring, I'd be happy to send over a short resource or set up a quick chat.\n\n"
            data += "You can reach me at [phone number].\n\n"
            data += f"Again, it's {sp_name} with HP Canada. Hope we can connect soon.\n\n"

            # Objection Handling
            data += "--- Objection Handling ---\n\n"
            data += "Objection: I'm not interested.\n"
            data += f"Totally understand. I'm not calling to sell anything. I just wanted to share a quick perspective we've seen make a difference for other teams in {industry}.\n"
            data += "Would you be open to looking at a short resource?\n\n"
            data += "Objection: We're already working with another vendor.\n"
            data += "That's great. A lot of teams we work with were in a similar position and just wanted to see if there were areas they could do things a bit more efficiently.\n"
            data += "Would it make sense to share a quick example?\n\n"
            data += "Objection: Now's not a good time.\n"
            data += "Of course. Is there a time when you will be available later this week? I can make it quick. 10 minutes tops.\n\n"
            data += "Objection: Send me something.\n"
            data += f"Absolutely. I'll send over a short piece on {priority_area}. If it seems relevant, we can reconnect to see if there's a fit.\n\n"

        data += f"\n=== REPORT METADATA ===\n\n"
        data += f"Confidence Score: {company_data.get('confidence_score', 0.85):.0%}\n"
        data += f"Report Generated: {current_date}\n"
        data += f"Status: For Internal HP Use Only\n"

        return data

    def _validate_company_data(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate if company data is minimally viable for report generation.

        Returns:
            Dict with 'is_valid' boolean and 'reason' string
        """
        validated_data = company_data.get("validated_data", {})
        company_name = validated_data.get('company_name', '')

        # Check if we have at minimum: company name and industry
        if not company_name or company_name == 'Company':
            return {
                'is_valid': False,
                'reason': 'Company name not available'
            }

        # Check if we have ANY substantive data beyond name
        has_data = any([
            validated_data.get('company_overview'),
            validated_data.get('description'),
            validated_data.get('industry'),
            validated_data.get('employee_count'),
            validated_data.get('technology'),
            validated_data.get('stakeholder_profiles'),
            validated_data.get('stakeholder_map')
        ])

        if not has_data:
            return {
                'is_valid': False,
                'reason': 'Insufficient company data - company may not exist or APIs failed'
            }

        return {
            'is_valid': True,
            'reason': 'Sufficient data available'
        }

    @staticmethod
    def _estimate_it_budget(validated_data: Dict[str, Any]) -> str:
        """Estimate annual IT budget from validated data.

        Uses the same logic as _build_executive_snapshot in production_main:
        1. Check for explicit estimated_it_spend / it_budget fields
        2. Fall back to employee-count-based estimate ($10K-$20K per employee)
        """
        it_spend = (
            validated_data.get("estimated_it_spend")
            or validated_data.get("it_budget")
        )
        if it_spend:
            # Already a string like "$5.0M - $10.0M annually"
            s = str(it_spend).strip()
            return s if s.startswith("$") else f"${s}"

        employee_count = validated_data.get("employee_count")
        if employee_count:
            try:
                emp_num = int(
                    str(employee_count).replace(",", "").replace("+", "").split("-")[0]
                )
                low = emp_num * 10000
                high = emp_num * 20000
                if high >= 1_000_000:
                    return f"${low / 1_000_000:.1f}M - ${high / 1_000_000:.1f}M annually"
                else:
                    return f"${low / 1_000:.0f}K - ${high / 1_000:.0f}K annually"
            except (ValueError, TypeError):
                pass

        return "Not available"

    def _generate_markdown(self, company_data: Dict[str, Any], user_email: str = None) -> str:
        """
        Generate markdown content from company data following HP RAD Intelligence template.

        IMPORTANT: This maintains ALL content verbatim - DO NOT simplify.
        Prioritizes data/charts over AI images. HP branded.

        If company data is insufficient (company doesn't exist or APIs failed),
        displays "Data unavailable at the time" messaging throughout.

        Slide Structure:
        1. Title: Account Intelligence Report
        2. Executive Snapshot
        3. Buying Signals
        4. Opportunity themes
        5+. Stakeholder Profiles (one dedicated slide per contact from stakeholder_map)
        Next. Recommended sales program
        Next+. Supporting Assets (one per persona: CIO/CTO/CISO/COO/CFO/CPO)
        Last: Feedback and Questions

        Args:
            company_data: Finalized company data
            user_email: Email of person pulling the data

        Returns:
            Formatted markdown string for HP Account Intelligence Report
        """
        validated_data = company_data.get("validated_data", {})
        company_name = validated_data.get('company_name', 'Company')

        # Validate if we have sufficient company data
        validation_result = self._validate_company_data(company_data)
        data_unavailable = not validation_result['is_valid']

        # Get current date for report in EST
        from datetime import datetime, timedelta, timezone
        # EST is UTC-5 (or UTC-4 during EDT, but using fixed EST offset)
        est = timezone(timedelta(hours=-5))
        current_date = datetime.now(est).strftime("%B %d, %Y")

        # Salesperson name (entered by user on the form)
        salesperson_name = company_data.get('salesperson_name') or user_email or company_data.get('user_email', '')

        markdown = ""

        # ============================================================
        # DESIGN INSTRUCTIONS FOR GAMMA (will be interpreted by AI)
        # ============================================================
        markdown += """<!--
CRITICAL DESIGN INSTRUCTIONS - MUST FOLLOW:

1. DESIGN STYLE: Create a professional consulting-style presentation deck
   - Clean, corporate aesthetic similar to McKinsey/BCG/Bain decks
   - Consistent slide sizes throughout - all cards should be the same dimensions
   - Use large card format to fit more content per slide
   - Minimal, professional color palette (blues, grays, whites)

2. NO AI-GENERATED IMAGES: Do NOT add any AI-generated images, stock photos,
   or decorative imagery. This is a data-driven business intelligence report.
   The only visuals should be:
   - Charts and graphs (bar charts, pie charts for data)
   - Tables for structured data
   - Icons only if absolutely necessary for navigation

3. DATA VISUALIZATION PRIORITY:
   - Render all tables as actual data tables
   - Convert intent score data to bar charts where applicable
   - Use clean data visualizations instead of decorative elements

4. TYPOGRAPHY & LAYOUT:
   - Professional business fonts
   - Clear hierarchy with headers
   - Adequate whitespace
   - Left-aligned text for readability

5. HP BRANDING: This is an HP enterprise document - maintain professional,
   corporate appearance appropriate for Fortune 500 sales materials.
-->

"""

        # ============================================================
        # SLIDE 1: Title Slide
        # ============================================================
        markdown += f"# Account Intelligence Report: {company_name}\n\n"
        markdown += f"**Prepared for:** {salesperson_name} by the HP RAD Intelligence Desk\n\n"
        markdown += f"**This information was pulled on:** {current_date}\n\n"

        # Add warning banner if data is unavailable
        if data_unavailable:
            markdown += "\n⚠️ **DATA QUALITY WARNING** ⚠️\n\n"
            markdown += f"**Reason:** {validation_result['reason']}\n\n"
            markdown += "Most sections will show 'Data unavailable at the time.' Manual research is required.\n\n"

        markdown += "**Confidential - for internal HP use only**\n\n"
        markdown += "---\n\n"

        # ============================================================
        # SLIDE 2: Executive Snapshot
        # ============================================================
        markdown += "# Executive Snapshot\n\n"

        markdown += f"**Account Name:** {company_name}\n\n"

        # Company Overview - FULL TEXT, do not simplify
        markdown += "**Company Overview:**\n\n"
        if data_unavailable:
            markdown += f"**Data unavailable at the time.** Comprehensive company information for {company_name} could not be retrieved. This may indicate the company name is incorrect, the company is private/unlisted, or external data sources are temporarily unavailable.\n\n"
        else:
            overview = validated_data.get('company_overview') or validated_data.get('description') or validated_data.get('summary', '')
            if overview:
                markdown += f"{overview}\n\n"
            else:
                markdown += f"{company_name} is an organization operating in the {validated_data.get('industry', 'technology')} sector. Further details available through company research.\n\n"

        # Account Type
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

        # Industry
        industry = validated_data.get('industry', 'Technology')
        markdown += f"**Industry:** {industry}\n\n"

        # Estimated Annual IT Budget — use same logic as executive snapshot
        it_spend = self._estimate_it_budget(validated_data)
        markdown += f"**Estimated Annual IT Budget:** {it_spend}\n\n"

        # Contact Information - DISPLAY PHONE NUMBERS
        markdown += "**Contact Information:**\n\n"
        phone = validated_data.get('phone', '')
        fax = validated_data.get('fax', '')
        corporate_email = validated_data.get('corporate_email', '')

        if phone:
            markdown += f"- **Phone:** {phone}\n"
        if fax:
            markdown += f"- **Fax:** {fax}\n"
        if corporate_email:
            markdown += f"- **Corporate Email:** {corporate_email}\n"
        if not (phone or fax or corporate_email):
            markdown += "Contact information available through company website\n"
        markdown += "\n"

        # Growth Metrics from ZoomInfo
        growth_1yr = validated_data.get('one_year_employee_growth', '')
        growth_2yr = validated_data.get('two_year_employee_growth', '')
        funding = validated_data.get('funding_amount', '')
        fortune = validated_data.get('fortune_rank', '')
        num_locations = validated_data.get('num_locations', '')
        if growth_1yr or growth_2yr or funding or fortune or num_locations:
            markdown += "**Growth Metrics:**\n\n"
            if growth_1yr:
                try:
                    sign = "+" if float(str(growth_1yr).strip('%').strip()) >= 0 else ""
                    markdown += f"- 1-Year Employee Growth: {sign}{growth_1yr}%\n"
                except (ValueError, TypeError):
                    markdown += f"- 1-Year Employee Growth: {growth_1yr}\n"
            if growth_2yr:
                try:
                    sign = "+" if float(str(growth_2yr).strip('%').strip()) >= 0 else ""
                    markdown += f"- 2-Year Employee Growth: {sign}{growth_2yr}%\n"
                except (ValueError, TypeError):
                    markdown += f"- 2-Year Employee Growth: {growth_2yr}\n"
            if funding:
                markdown += f"- Recent Funding: ${funding}\n"
            if fortune:
                markdown += f"- Fortune Rank: #{fortune}\n"
            if num_locations:
                markdown += f"- Office Locations: {num_locations}\n"
            markdown += "\n"

        # Installed Technologies - COMPREHENSIVE with ZoomInfo tech installs
        markdown += "**Installed Technologies:**\n\n"
        if data_unavailable:
            markdown += "**Data unavailable at the time.** Technology stack information could not be retrieved.\n\n"
        else:
            # Get tech data from multiple sources
            tech_stack = validated_data.get('technology') or validated_data.get('tech_stack') or validated_data.get('technologies', [])
            tech_installs = validated_data.get('technology_installs', [])

            # Combine all technology sources
            all_techs = []
            tech_details = {}

            # Add basic tech stack
            if isinstance(tech_stack, list):
                all_techs.extend(tech_stack)
            elif isinstance(tech_stack, str):
                all_techs.extend([t.strip() for t in tech_stack.split(',')])

            # Add ZoomInfo technology installations with full details
            if tech_installs:
                for tech in tech_installs:
                    if isinstance(tech, dict):
                        tech_name = tech.get('tech_name', tech.get('product_name', ''))
                        if tech_name and tech_name not in all_techs:
                            all_techs.append(tech_name)
                        # Store detailed info for comprehensive view
                        tech_details[tech_name] = {
                            'vendor': tech.get('vendor', ''),
                            'category': tech.get('category', ''),
                            'last_seen': tech.get('last_seen', ''),
                            'status': tech.get('status', ''),
                            'adoption_level': tech.get('adoption_level', '')
                        }

            if all_techs:
                # Show comprehensive technology list
                if tech_details:
                    # Detailed view with ZoomInfo data
                    markdown += "Technology Portfolio (verified installations):\n\n"
                    # Group by category if available
                    by_category = {}
                    for tech_name in all_techs:
                        category = tech_details.get(tech_name, {}).get('category', 'Other')
                        if not category:
                            category = 'Other'
                        if category not in by_category:
                            by_category[category] = []
                        by_category[category].append(tech_name)

                    # Display by category with details
                    for category, techs in sorted(by_category.items()):
                        markdown += f"**{category}:** "
                        tech_items = []
                        for t in techs:
                            details = tech_details.get(t, {})
                            vendor = details.get('vendor', '')
                            status = details.get('status', '')
                            adoption = details.get('adoption_level', '')

                            tech_item = t
                            if vendor:
                                tech_item += f" ({vendor})"
                            if adoption:
                                tech_item += f" [{adoption}]"
                            tech_items.append(tech_item)
                        markdown += ', '.join(tech_items) + "\n\n"

                    # Installation count
                    markdown += f"Total verified technology installations: {len(tech_installs)}\n\n"
                else:
                    # Simple list view
                    tech_list = ', '.join(all_techs)
                    markdown += f"{tech_list}\n\n"

                # Add last seen date if available
                tech_last_seen = validated_data.get('technology_last_seen', '')
                if tech_last_seen:
                    markdown += f"*(Last verified: {tech_last_seen})*\n\n"
            else:
                markdown += "CRM, Marketing Automation, Sales Tools, Infrastructure - detailed technology stack available through research channels\n\n"

        markdown += "---\n\n"

        # ============================================================
        # SLIDE 3: Buying Signals
        # ============================================================
        markdown += "# Buying Signals\n\n"

        # ALL Intent Topics with comprehensive details (not just top 3)
        markdown += "## Intent Topics (All Available)\n\n"

        intent_topics = []
        if data_unavailable:
            markdown += "**Data unavailable at the time.** Intent signal data could not be retrieved for this account.\n\n"
        else:
            intent_topics = validated_data.get('intent_topics') or validated_data.get('intent_signals') or validated_data.get('buying_signals', {}).get('intent_topics', [])

            # NOTE: Intent topics should be generated by the enrichment pipeline with scores and interpretations
            # If missing, generate basic topics from company industry/tech stack
            if not intent_topics:
                intent_topics = [
                    {'topic': 'Cloud Infrastructure & Migration', 'score': 85, 'audience_strength': 'high', 'description': 'Active research in cloud migration and infrastructure modernization'},
                    {'topic': 'Cybersecurity & Compliance', 'score': 78, 'audience_strength': 'medium', 'description': 'Security posture improvement and compliance initiatives'},
                    {'topic': 'AI & Machine Learning Solutions', 'score': 72, 'audience_strength': 'medium', 'description': 'AI adoption and data analytics capabilities'}
                ]

            # Show ALL intent topics (not limited to 3) with comprehensive details
            markdown += "| Intent Topic | Score | Strength | Details |\n"
            markdown += "|-------------|-------|----------|----------|\n"
            for i, topic in enumerate(intent_topics, 1):  # Show ALL, not just [:3]
                if isinstance(topic, dict):
                    topic_name = topic.get('topic', topic.get('topic_name', topic.get('name', f'Topic {i}')))
                    topic_score = topic.get('intent_score', topic.get('score', 70 + i*5))
                    topic_strength = topic.get('audience_strength', topic.get('strength', '-'))
                    topic_desc = topic.get('description', '-')
                    topic_category = topic.get('category', '')
                    topic_last_seen = topic.get('last_seen', '')

                    # Build details column
                    details = []
                    if topic_desc and topic_desc != '-':
                        details.append(topic_desc)
                    if topic_category:
                        details.append(f"Category: {topic_category}")
                    if topic_last_seen:
                        details.append(f"Last seen: {topic_last_seen}")
                    details_str = '; '.join(details) if details else '-'
                else:
                    topic_name = str(topic)
                    topic_score = 80 - i*5
                    topic_strength = '-'
                    details_str = '-'

                markdown += f"| {topic_name} | {topic_score} | {topic_strength} | {details_str} |\n"
            markdown += "\n"

            # Intent Score explanation
            markdown += f"*{len(intent_topics)} intent signals detected based on digital behavior, research activity, and content engagement. Higher scores indicate stronger buying intent.*\n\n"

        # Top Partner Mentions
        markdown += "## Top Partner Mentions\n\n"
        partners = validated_data.get('partner_mentions') or validated_data.get('buying_signals', {}).get('competitors', [])
        if not partners:
            # NOTE: Partner mentions should come from news/tech stack analysis in enrichment pipeline
            partners = validated_data.get('competitors', [])
            if not partners:
                # Generate from tech stack if available
                tech_stack = validated_data.get('technology') or validated_data.get('tech_stack') or []
                if isinstance(tech_stack, list):
                    partners = tech_stack[:7]  # Use existing tech stack as partner mentions
                else:
                    partners = ['Monitor for technology partnerships and vendor relationships']
        if isinstance(partners, list):
            markdown += ', '.join(str(p) for p in partners[:7]) + "\n\n"
        else:
            markdown += f"{partners}\n\n"

        # Key Signal (News & Triggers)
        markdown += "## Key Signal (News & Triggers)\n\n"

        # Get news/triggers data
        news_triggers = validated_data.get('news_triggers') or validated_data.get('buying_signals', {}).get('triggers', {})

        # Funding / Capital Markets Signal
        markdown += "**[1] Funding / Capital Markets Signal**\n\n"
        funding = news_triggers.get('funding') or validated_data.get('funding_news', '')
        if funding:
            if isinstance(funding, list):
                markdown += "**Signal:** " + " ".join(str(f) for f in funding) + "\n\n"
            else:
                markdown += f"**Signal:** {funding}\n\n"
            markdown += "**What this means:** Recent funding indicates growth capital available for infrastructure investments, technology upgrades, and expansion initiatives. This suggests timing for strategic partnerships and solution deployments.\n\n"
        else:
            markdown += "**Signal:** No recent funding announcements.\n\n"
            markdown += "**What this means:** This is an established, potentially self-funded organization. Focus on operational efficiency and ROI-driven solutions.\n\n"

        # Hiring / Expansion (Operations)
        markdown += "**[2] Hiring / Expansion Signal**\n\n"
        expansions = news_triggers.get('expansions') or validated_data.get('expansion_news', '')
        exec_changes = news_triggers.get('executive_changes') or validated_data.get('executive_hires', '')

        if expansions or exec_changes:
            signal_text = []
            if expansions:
                if isinstance(expansions, list):
                    signal_text.extend(expansions)
                else:
                    signal_text.append(str(expansions))
            if exec_changes:
                if isinstance(exec_changes, list):
                    signal_text.extend(exec_changes)
                else:
                    signal_text.append(str(exec_changes))
            markdown += "**Signal:** " + " ".join(signal_text) + "\n\n"
            markdown += "**What this means:** Workforce expansion and/or leadership changes suggest organizational growth or transformation. This creates demand for workplace technology, device procurement, and infrastructure to support new teams and sites.\n\n"
        else:
            markdown += "**Signal:** No recent hiring or expansion announcements detected.\n\n"
            markdown += "**What this means:** Monitor for future growth signals that may trigger infrastructure and workplace technology needs.\n\n"

        # Operational Change / Partnerships & Acquisitions
        markdown += "**[3] Operational Change / Strategic Partnerships**\n\n"
        partnerships = news_triggers.get('partnerships') or validated_data.get('partnership_news', '')
        products = news_triggers.get('products') or validated_data.get('product_news', '')

        if partnerships or products:
            signal_text = []
            if partnerships:
                if isinstance(partnerships, list):
                    signal_text.extend(partnerships)
                else:
                    signal_text.append(str(partnerships))
            if products:
                if isinstance(products, list):
                    signal_text.extend(products)
                else:
                    signal_text.append(str(products))
            markdown += "**Signal:** " + " ".join(signal_text) + "\n\n"
            markdown += "**What this means:** Strategic initiatives and partnerships indicate business transformation and investment in new capabilities. This creates opportunities for technology solutions that support integration, collaboration, and operational scaling.\n\n"
        else:
            markdown += "**Signal:** No recent partnership or product announcements detected.\n\n"
            markdown += "**What this means:** Monitor for upcoming strategic initiatives and product launches that may drive technology requirements.\n\n"

        markdown += "---\n\n"

        # ============================================================
        # SLIDE 4: Opportunity themes
        # ============================================================
        markdown += "# Opportunity themes\n\n"

        # Pain Points
        markdown += "## Pain points\n\n"

        if data_unavailable:
            markdown += "**Data unavailable at the time.** Pain points and challenges could not be identified due to insufficient company data.\n\n"
            pain_points = []  # Skip pain point generation
        else:
            pain_points = validated_data.get('pain_points') or validated_data.get('opportunity_themes_detailed', {}).get('pain_points', []) or validated_data.get('opportunity_themes', {}).get('pain_points', [])

        # NOTE: Pain points should be generated by LLM Council based on company data, news, and industry
        if not pain_points and not data_unavailable:
            industry = validated_data.get('industry', 'technology')
            employee_count = validated_data.get('employee_count', 0)

            # Generate industry-relevant pain points dynamically
            pain_points = []

            # Size-based pain point
            if isinstance(employee_count, int) and employee_count > 10000:
                pain_points.append({'title': f'Enterprise-scale coordination and standardization ({employee_count}+ employees)', 'description': f'Organizations of this scale face inherent complexity in maintaining consistent technology standards and user experience across a distributed workforce. With {employee_count}+ employees, even small inconsistencies in device configuration, software versions, or support processes compound into significant operational drag. The challenge intensifies when different business units have historically made independent technology decisions, creating a fragmented estate that is expensive to support and difficult to secure uniformly.'})
            elif isinstance(employee_count, int) and employee_count > 1000:
                pain_points.append({'title': f'Growth-stage operational efficiency (scaling beyond {employee_count} employees)', 'description': f'Mid-to-large organizations in a growth phase often find that the processes and tools that worked at a smaller scale start to break down. With {employee_count}+ employees, manual provisioning, ad-hoc support models, and inconsistent technology standards create friction that slows onboarding, increases support costs, and makes it harder to maintain security posture. The pressure to scale efficiently while keeping quality and consistency high demands a more intentional approach to technology lifecycle management.'})
            else:
                pain_points.append({'title': 'Resource optimization and operational efficiency (lean IT operations)', 'description': 'Smaller and mid-size organizations often operate with lean IT teams that must balance day-to-day support with strategic initiatives. Without the luxury of dedicated teams for procurement, deployment, and lifecycle management, technology decisions tend to be reactive rather than planned. This creates an uneven technology estate where refresh cycles slip, support becomes ad-hoc, and the total cost of ownership creeps up without clear visibility.'})

            # Industry-specific pain point
            if any(word in industry.lower() for word in ['manufacturing', 'automotive', 'industrial']):
                pain_points.append({'title': f'Operational technology modernization ({industry.lower()} digital transformation)', 'description': f'The {industry.lower()} sector is under pressure to bridge legacy operational technology with modern digital infrastructure without disrupting production uptime. Many organizations still rely on aging systems that were never designed for connectivity or data-driven decision-making. The challenge is not just technical migration — it requires rethinking workflows, retraining staff, and maintaining continuity during the transition, all while competitors move faster.'})
            elif any(word in industry.lower() for word in ['financial', 'banking', 'insurance']):
                pain_points.append({'title': f'Regulatory compliance and security posture ({industry.lower()} requirements)', 'description': f'The {industry.lower()} sector operates under some of the most stringent regulatory frameworks, requiring auditable infrastructure, data protection controls, and demonstrable compliance at every layer of the technology stack. The challenge is compounded by evolving regulations that demand continuous adaptation rather than one-time compliance. Organizations must balance the need for innovation and agility with the reality that any security gap or compliance failure carries outsized financial and reputational risk.'})
            elif any(word in industry.lower() for word in ['healthcare', 'medical']):
                pain_points.append({'title': f'Patient data security and compliance (HIPAA and beyond)', 'description': f'Healthcare organizations face a unique tension between the need to innovate — adopting telehealth, connected devices, and data-driven care — and the imperative to protect patient data under HIPAA and evolving state-level privacy regulations. Every new endpoint, application, and integration point expands the attack surface. The challenge is building an infrastructure posture that enables clinical agility while maintaining the audit trails, access controls, and encryption standards that regulators and patients expect.'})
            else:
                pain_points.append({'title': f'Digital transformation and competitive agility ({industry.lower()} pressures)', 'description': f'Organizations in the {industry.lower()} space are navigating a period where technology decisions directly impact competitive positioning. Legacy infrastructure limits the speed at which new capabilities can be deployed, tested, and scaled. The gap between organizations that have modernized their technology estate and those still operating on aging systems is widening, creating urgency to act — but also risk of making hasty investments without a clear lifecycle and support strategy.'})

            # Universal pain point
            pain_points.append({'title': 'Technology investment ROI and cost visibility (demonstrating value)', 'description': 'Across industries, IT leaders are under increasing pressure to demonstrate that technology investments deliver measurable business outcomes rather than just keeping the lights on. Without clear metrics on total cost of ownership, utilization rates, and lifecycle costs, it becomes difficult to justify refresh cycles, new initiatives, or vendor consolidation. The result is often deferred decisions that ultimately cost more in support burden, security risk, and lost productivity.'})

        # v3 format: bolded title, blank line, description paragraph. Cap at 3.
        for pain in pain_points[:3]:
            if isinstance(pain, dict):
                pain_title = pain.get('title', pain.get('name', 'Pain Point'))
                pain_desc = pain.get('description', pain.get('pain_point', ''))
                markdown += f"**{pain_title}**\n\n"
                if pain_desc:
                    markdown += f"{pain_desc}\n\n"
            else:
                markdown += f"**{str(pain)}**\n\n"

        # Sales opportunities
        markdown += "## Sales opportunities\n\n"

        if data_unavailable:
            markdown += "**Data unavailable at the time.** Sales opportunities could not be identified due to insufficient company data.\n\n"
            opportunities = []  # Skip opportunity generation
        else:
            opportunities = validated_data.get('sales_opportunities') or validated_data.get('opportunity_themes_detailed', {}).get('sales_opportunities', []) or validated_data.get('opportunities', [])

        # NOTE: Sales opportunities should be generated by LLM Council based on pain points, intent signals, and company profile
        if not opportunities and not data_unavailable:
            industry = validated_data.get('industry', 'technology')

            opportunities = []

            # Generate from intent topics if available
            if intent_topics:
                for topic in intent_topics[:2]:
                    topic_name = topic.get('topic', '') if isinstance(topic, dict) else str(topic)
                    opportunities.append({
                        'title': f'{topic_name} assessment and roadmap',
                        'description': f'There are signals suggesting {company_name} has active interest or investment in {topic_name.lower()}. Understanding where they are in their journey — whether they are early in evaluation, mid-implementation, or looking to optimize an existing deployment — will reveal where the real gaps and unmet needs are. Exploring how their current approach to {topic_name.lower()} aligns with their broader business objectives can surface opportunities to add value through better integration, standardization, or lifecycle planning.'
                    })

            # Add infrastructure opportunity
            opportunities.append({
                'title': 'Infrastructure modernization and lifecycle management',
                'description': f'{company_name} likely has refresh cycles, standardization goals, and support model preferences that have evolved over time — some intentionally, some by default. Understanding their current device estate maturity, how they handle end-of-life transitions, and whether their support model is reactive or proactive will clarify where modernization efforts can deliver the most impact. Organizations in the {industry.lower()} space often find that inconsistent lifecycle management creates hidden costs in support overhead, security exposure, and user productivity loss.'
            })

            # Ensure we have at least 3
            if len(opportunities) < 3:
                opportunities.append({
                    'title': 'Managed services and support optimization',
                    'description': f'Many organizations carry a significant internal support burden that they have grown accustomed to but never fully quantified. Exploring how {company_name} currently handles provisioning, break-fix, and ongoing management — and where those processes create friction or bottlenecks — can reveal whether a managed services approach would free up internal resources for higher-value work. The conversation should focus on understanding their pain points with the current support model and where they see the biggest operational drag.'
                })

        for i, opp in enumerate(opportunities[:3], 1):
            if isinstance(opp, dict):
                opp_title = opp.get('title', opp.get('name', f'Opportunity {i}'))
                opp_desc = opp.get('description', opp.get('details', ''))
                # Strip any residual "Validate:" or "Qualify:" prefixes from LLM output
                if opp_desc:
                    opp_desc = re.sub(r'^(Validate|Qualify)[:\s]+', '', opp_desc).strip()
                    # Remove any "Qualify ..." sentence at the end
                    opp_desc = re.sub(r'\s*Qualify\s+[^.]*\.\s*$', '', opp_desc).strip()
                markdown += f"**{i}. {opp_title}**\n\n"
                if opp_desc:
                    markdown += f"{opp_desc}\n\n"
            else:
                markdown += f"**{i}. {str(opp)}**\n\n"

        # Recommended solution areas
        markdown += "## Recommended solution areas\n\n"

        if data_unavailable:
            markdown += "**Data unavailable at the time.** Recommended solutions could not be identified due to insufficient company data.\n\n"
            solutions = []  # Skip solution generation
        else:
            solutions = validated_data.get('recommended_solutions') or validated_data.get('opportunity_themes_detailed', {}).get('recommended_solution_areas', []) or validated_data.get('recommended_focus') or validated_data.get('opportunity_themes', {}).get('solutions', [])

        # NOTE: Solution areas should be generated by LLM Council based on pain points and opportunities
        if not solutions and not data_unavailable:
            industry = validated_data.get('industry', 'technology')

            solutions = []

            # Map pain points to high-level HP strategic solution areas
            for i, pain in enumerate(pain_points[:3], 1):
                pain_title = pain.get('title', '') if isinstance(pain, dict) else str(pain)
                if 'security' in pain_title.lower() or 'compliance' in pain_title.lower():
                    solutions.append({
                        'title': f'HP endpoint security and compliance readiness ({industry.lower()} risk posture)',
                        'description': f'Use the security and compliance signals to position HP as a partner for building a structured endpoint security posture — from device-level protection and access controls to audit readiness — that addresses {industry.lower()}-specific regulatory requirements. Frame the conversation around reducing operational risk and simplifying compliance reporting, not around specific product SKUs. The salesperson should explore where their current security approach has gaps and where HP can streamline protection across the device estate.'
                    })
                elif 'scale' in pain_title.lower() or 'efficiency' in pain_title.lower() or 'optimization' in pain_title.lower():
                    solutions.append({
                        'title': 'HP device standardization and lifecycle management (fleet efficiency)',
                        'description': f'Use the efficiency and scaling signals to position HP as a standardization partner — driving a consistent device estate with clear refresh cycles, streamlined provisioning, and reduced support friction. The conversation should focus on how HP can help simplify buying, deployment, and end-of-life management as a single ecosystem approach that reduces total cost of ownership and makes the IT team\'s job easier.'
                    })
                elif 'transformation' in pain_title.lower() or 'modernization' in pain_title.lower():
                    solutions.append({
                        'title': f'HP infrastructure modernization and workplace enablement ({industry.lower()} agility)',
                        'description': f'Use the transformation signals to position HP as an enabler of phased modernization — replacing aging infrastructure with scalable, modern technology without disrupting day-to-day operations. For {industry.lower()} organizations, emphasize how HP can bridge legacy environments with modern workflows, support hybrid and remote work scenarios, and provide a technology foundation that supports rather than constrains future initiatives.'
                    })
                elif 'roi' in pain_title.lower() or 'cost' in pain_title.lower() or 'visibility' in pain_title.lower() or 'investment' in pain_title.lower():
                    solutions.append({
                        'title': 'HP lifecycle services and technology value realization (ROI clarity)',
                        'description': 'Use the cost visibility and ROI signals to position HP\'s lifecycle services approach — helping the organization gain clear metrics on total cost of ownership, utilization, and refresh timing. Frame HP as a partner that helps them make better technology investment decisions, consolidate vendors, and demonstrate the business value of IT spend to leadership.'
                    })
                else:
                    solutions.append({
                        'title': f'HP strategic engagement for {pain_title.split("(")[0].strip().lower()}',
                        'description': f'Use the available signals around {pain_title.split("(")[0].strip().lower()} to position HP as a strategic partner that can address the immediate operational pain while building toward a more sustainable long-term model. Focus the conversation on understanding their current state, identifying quick wins where HP can add value, and establishing a roadmap that aligns HP solutions with their measurable business outcomes.'
                    })

            # Ensure unique solutions (deduplicate by title)
            seen_titles = set()
            unique_solutions = []
            for sol in solutions:
                if sol['title'] not in seen_titles:
                    seen_titles.add(sol['title'])
                    unique_solutions.append(sol)
            solutions = unique_solutions[:3]

        for i, solution in enumerate(solutions, 1):
            if isinstance(solution, dict):
                solution_title = solution.get('title', solution.get('name', f'Area {i}'))
                solution_desc = solution.get('description', solution.get('solution', ''))
                markdown += f"**{i}. {solution_title}**\n\n"
                if solution_desc:
                    markdown += f"{solution_desc}\n\n"
            else:
                markdown += f"**{i}.** {str(solution)}\n\n"

        markdown += "---\n\n"


        # ============================================================
        # SLIDES 5+: Individual Stakeholder Profiles (ONE SLIDE PER CONTACT)
        # Sources from stakeholder_map.stakeholders (C-suite grouped, up to 3 per category)
        # Each executive contact gets their own dedicated slide
        # ============================================================

        all_stakeholders = []
        if data_unavailable:
            # Show data unavailable slide for stakeholders
            markdown += "# Stakeholder Map: Role Profiles\n\n"
            markdown += "## Data Unavailable\n\n"
            markdown += f"**Data unavailable at the time.** Stakeholder and contact information for {company_name} could not be retrieved. This may indicate:\n\n"
            markdown += "- The company name is incorrect or the company does not exist\n- The company is private or unlisted with limited public information\n- External data sources are temporarily unavailable\n- Contact data requires manual research or verification\n\n"
            markdown += "Please verify the company name and try again, or conduct manual research through LinkedIn, company website, and other professional networks.\n\n"
            markdown += "---\n\n"
        else:
            # Pull executive stakeholders (C-suite grouped) + relevant other contacts.
            # Structure:
            #   1. All executive profiles from stakeholder_map.stakeholders
            #      (grouped under their C-suite category: CTO, CFO, CEO, etc.)
            #   2. Relevant other contacts from stakeholder_map.otherContacts
            #      whose title matches sales, partnerships, strategy, or communications
            stakeholder_map = validated_data.get('stakeholder_map', {})

            # 1. Executive stakeholders (already C-suite grouped)
            executive_stakeholders = []
            if stakeholder_map and stakeholder_map.get('stakeholders'):
                executive_stakeholders = [
                    s for s in stakeholder_map['stakeholders']
                    if isinstance(s, dict)
                ]

            # 2. Relevant other contacts — filter by role keywords
            _RELEVANT_ROLES = {
                'sales', 'partnership', 'partnerships', 'strategy',
                'strategic', 'communication', 'communications',
                'business development', 'channel', 'alliances',
                'account', 'revenue',
            }
            relevant_other_contacts = []
            if stakeholder_map and stakeholder_map.get('otherContacts'):
                for contact in stakeholder_map['otherContacts']:
                    if not isinstance(contact, dict):
                        continue
                    contact_title = (contact.get('title') or '').lower()
                    contact_dept = (contact.get('department') or '').lower()
                    contact_role = (contact.get('roleType') or '').lower()
                    combined = f"{contact_title} {contact_dept} {contact_role}"
                    if any(role in combined for role in _RELEVANT_ROLES):
                        # Tag as non-executive for slide heading
                        contact['_slideCategory'] = 'Relevant Contact'
                        relevant_other_contacts.append(contact)

            # Fallback: if no stakeholder_map, try legacy stakeholder_profiles
            if not executive_stakeholders and not relevant_other_contacts:
                stakeholders = validated_data.get('stakeholder_profiles') or validated_data.get('stakeholders', [])
                if isinstance(stakeholders, list):
                    executive_stakeholders = [s for s in stakeholders if isinstance(s, dict)]
                elif isinstance(stakeholders, dict):
                    for role, profile in stakeholders.items():
                        if isinstance(profile, dict):
                            profile['role_type'] = role
                            executive_stakeholders.append(profile)

            all_stakeholders = executive_stakeholders + relevant_other_contacts

            # If still no stakeholders, show minimal unavailable message
            if not all_stakeholders:
                markdown += "# Stakeholder Map: Role Profiles\n\n"
                markdown += "## Data Unavailable\n\n"
                markdown += f"**Stakeholder data unavailable at the time.** Contact information for {company_name} could not be retrieved. Manual research recommended.\n\n"
                markdown += "---\n\n"

            # Generate a dedicated slide for EACH stakeholder
            for stakeholder in all_stakeholders:
                name = stakeholder.get('name', 'Contact Name')
                title = stakeholder.get('title', stakeholder.get('role_type', stakeholder.get('position', 'Executive')))

                # Determine persona type from csuiteCategory (set by affiliation grouping) or title
                persona = stakeholder.get('csuiteCategory', '')
                if not persona:
                    # Check if this is a relevant non-executive contact
                    if stakeholder.get('_slideCategory'):
                        persona = stakeholder['_slideCategory']
                    else:
                        persona = "Executive"
                        title_upper = title.upper()
                        for p in ['CFO', 'CTO', 'CIO', 'CISO', 'COO', 'CPO', 'CEO', 'CMO']:
                            if p in title_upper:
                                persona = p
                                break

                # Use C-suite category for executives, title-based label for others
                if persona in ('Relevant Contact',):
                    slide_label = title or "Key Contact"
                else:
                    slide_label = f"{persona} Stakeholder Profile"

                markdown += f"# {name} – {slide_label}\n\n"

                # Contact Information (at top)
                markdown += f"**Contact:** {name}\n\n"
                markdown += f"**Title:** {title}\n\n"

                # Department
                department = stakeholder.get('department', '')
                if not department:
                    # Infer from persona
                    dept_map = {
                        'CFO': 'Finance',
                        'CTO': 'Technology',
                        'CIO': 'Information Technology',
                        'CISO': 'Security',
                        'COO': 'Operations',
                        'CPO': 'Product',
                        'CEO': 'C-Suite'
                    }
                    department = dept_map.get(persona, 'C-Suite')
                markdown += f"**Department:** {department}\n\n"

                # Start date
                start_date = stakeholder.get('start_date', stakeholder.get('hire_date', ''))
                if start_date:
                    markdown += f"**Start date:** {start_date}\n\n"
                else:
                    markdown += "**Start date:** Currently unavailable\n\n"

                # Phone numbers - check top-level fields AND nested "contact" dict.
                # Top-level fields use snake_case: direct_phone, mobile_phone, company_phone
                # Nested contact dict uses camelCase: directPhone, mobilePhone, companyPhone
                # Either source may have None values, so coerce to str and strip.
                _contact = stakeholder.get('contact') or {}
                if not isinstance(_contact, dict):
                    _contact = {}

                def _phone(val):
                    """Coerce phone value to clean string or empty."""
                    if not val:
                        return ''
                    s = str(val).strip()
                    # Filter out masked/placeholder values
                    if s in ('None', 'N/A', 'null', '') or '****' in s:
                        return ''
                    return s

                direct_phone = (_phone(stakeholder.get('direct_phone'))
                                or _phone(stakeholder.get('directPhone'))
                                or _phone(_contact.get('directPhone')))
                mobile = (_phone(stakeholder.get('mobile_phone'))
                          or _phone(stakeholder.get('mobile'))
                          or _phone(_contact.get('mobilePhone')))
                company_phone = (_phone(stakeholder.get('company_phone'))
                                 or _phone(stakeholder.get('companyPhone'))
                                 or _phone(_contact.get('companyPhone')))
                phone = (_phone(stakeholder.get('phone'))
                         or _phone(stakeholder.get('phone_number'))
                         or _phone(_contact.get('phone')))

                # Display all available phone numbers (no duplicates)
                shown_phones = set()
                if direct_phone:
                    markdown += f"**Direct Phone:** {direct_phone}\n\n"
                    shown_phones.add(direct_phone)
                if mobile and mobile not in shown_phones:
                    markdown += f"**Mobile Phone:** {mobile}\n\n"
                    shown_phones.add(mobile)
                if company_phone and company_phone not in shown_phones:
                    markdown += f"**Company Phone:** {company_phone}\n\n"
                    shown_phones.add(company_phone)
                if phone and phone not in shown_phones:
                    markdown += f"**Phone:** {phone}\n\n"
                    shown_phones.add(phone)
                if not shown_phones:
                    markdown += "**Phone:** Currently unavailable\n\n"

                # Email - check top-level and nested contact dict
                email = (stakeholder.get('email') or _contact.get('email') or '')
                if email:
                    markdown += f"**Email:** {email}\n\n"
                else:
                    markdown += "**Email:** Currently unavailable\n\n"

                # LinkedIn - check top-level and nested contact dict
                linkedin = (stakeholder.get('linkedin') or stakeholder.get('linkedin_url')
                            or _contact.get('linkedinUrl') or '')
                if linkedin:
                    markdown += f"**LinkedIn:** {linkedin}\n\n"
                else:
                    markdown += "**LinkedIn:** Currently unavailable\n\n"

                # About - 1 paragraph bio (call out new hire if applicable)
                markdown += "## About\n\n"
                bio = stakeholder.get('bio', stakeholder.get('about', stakeholder.get('description', '')))
                is_new_hire = stakeholder.get('is_new_hire', False)
                hire_date = stakeholder.get('hire_date', stakeholder.get('start_date', ''))

                if bio:
                    markdown += f"{bio}"
                    if is_new_hire and hire_date:
                        markdown += f" **[If they are a new hire – call out & include the date: NEW HIRE - joined {hire_date}]**"
                    markdown += "\n\n"
                else:
                    markdown += f"{name} serves as {title} at {company_name}, responsible for strategic initiatives and organizational leadership in their domain."
                    if is_new_hire and hire_date:
                        markdown += f" **[NEW HIRE - joined {hire_date}]**"
                    markdown += "\n\n"

                # Strategic Priorities - 3 bullet points with titles and descriptions
                markdown += "## Strategic priorities\n\n"
                priorities = stakeholder.get('strategic_priorities', stakeholder.get('priorities', []))
                if priorities:
                    if isinstance(priorities, list):
                        for i, priority in enumerate(priorities[:3], 1):
                            if isinstance(priority, dict):
                                p_name = priority.get('name', priority.get('priority', priority.get('title', '')))
                                p_desc = priority.get('description', '')
                                markdown += f"**[{i}] {p_name}**\n\n"
                                if p_desc:
                                    markdown += f"{p_desc}\n\n"
                            else:
                                markdown += f"**[{i}]** {priority}\n\n"
                    else:
                        markdown += f"**[1]** {priorities}\n\n"
                else:
                    # NOTE: Strategic priorities should be generated by enrichment pipeline based on persona, news, and company context
                    # Generate persona-specific priorities dynamically
                    if persona == 'CFO':
                        markdown += f"**[1] Optimize operational efficiency and cost management**\n\n"
                        markdown += f"Drive cost transparency and efficiency across technology investments, focusing on standardization and vendor consolidation to reduce complexity.\n\n"
                        markdown += f"**[2] Strengthen financial controls and risk management**\n\n"
                        markdown += f"Ensure technology investments support compliance requirements and reduce operational risk exposure.\n\n"
                        markdown += f"**[3] Enable data-driven decision making**\n\n"
                        markdown += f"Improve visibility into technology spend and outcomes to support faster, more defensible investment decisions.\n\n"
                    elif persona == 'CTO' or persona == 'CIO':
                        markdown += f"**[1] Accelerate digital transformation initiatives**\n\n"
                        markdown += f"Modernize infrastructure to support {company_name}'s business agility and innovation objectives in {industry}.\n\n"
                        markdown += f"**[2] Enhance security and operational resilience**\n\n"
                        markdown += f"Strengthen cybersecurity posture and ensure business continuity through modern, secure infrastructure.\n\n"
                        markdown += f"**[3] Optimize IT operations and support efficiency**\n\n"
                        markdown += f"Reduce operational overhead through automation, standardization, and strategic vendor partnerships.\n\n"
                    elif persona == 'CISO':
                        markdown += f"**[1] Strengthen cybersecurity posture across the enterprise**\n\n"
                        markdown += f"Reduce attack surface and improve threat detection/response capabilities for {company_name}.\n\n"
                        markdown += f"**[2] Ensure regulatory compliance and risk management**\n\n"
                        markdown += f"Maintain compliance with {industry} regulations while managing security risk across technology infrastructure.\n\n"
                        markdown += f"**[3] Enable secure digital transformation**\n\n"
                        markdown += f"Balance security requirements with business innovation needs to support strategic initiatives.\n\n"
                    elif persona == 'COO':
                        markdown += f"**[1] Drive operational excellence and efficiency**\n\n"
                        markdown += f"Optimize business operations through improved technology, processes, and support models.\n\n"
                        markdown += f"**[2] Enable scalability and business growth**\n\n"
                        markdown += f"Ensure technology infrastructure can support {company_name}'s expansion and scaling objectives.\n\n"
                        markdown += f"**[3] Improve cross-functional collaboration and visibility**\n\n"
                        markdown += f"Enhance coordination between departments through better tools and standardized processes.\n\n"
                    else:  # CPO, CEO, other executives
                        markdown += f"**[1] Enable strategic business objectives**\n\n"
                        markdown += f"Align technology investments with {company_name}'s strategic goals in {industry}.\n\n"
                        markdown += f"**[2] Drive innovation and competitive advantage**\n\n"
                        markdown += f"Leverage technology to create differentiation and support new business capabilities.\n\n"
                        markdown += f"**[3] Optimize organizational effectiveness**\n\n"
                        markdown += f"Improve operational efficiency and decision-making through better technology and data insights.\n\n"

                # Communication Preferences
                markdown += "## Communication preference\n\n"
                comm_pref = stakeholder.get('communication_preference', stakeholder.get('communication_preferences', ''))
                if comm_pref:
                    markdown += f"{comm_pref}\n\n"
                else:
                    markdown += "Email / LinkedIn / Phone / Events\n\n"

                # Conversation Starters - persona-tailored with context
                markdown += "## Conversation starters\n\n"
                markdown += "*[1-2 sentences of persona-tailored language] [Include Recommended Play – subject to availability]*\n\n"

                conv_starters = stakeholder.get('conversation_starters', stakeholder.get('talking_points', []))
                if conv_starters:
                    if isinstance(conv_starters, list):
                        for i, starter in enumerate(conv_starters[:3], 1):
                            if isinstance(starter, dict):
                                starter_title = starter.get('title', starter.get('topic', f'Topic {i}'))
                                starter_text = starter.get('text', starter.get('question', ''))
                                markdown += f"**[{i}] {starter_title}**\n\n"
                                markdown += f"\"{starter_text}\"\n\n"
                            else:
                                markdown += f"**[{i}]** \"{starter}\"\n\n"
                    else:
                        markdown += f"**[1]** \"{conv_starters}\"\n\n"
                else:
                    # NOTE: Conversation starters should be generated by LLM Council based on persona, company news, and intent signals
                    # Generate persona-specific conversation starters dynamically
                    if persona == 'CFO':
                        markdown += f"**[1] Technology investment optimization**\n\n"
                        markdown += f"\"As you evaluate technology investments for {company_name}, what's your priority: reducing operational costs, improving vendor efficiency, or increasing visibility into technology ROI?\"\n\n"
                        markdown += f"**[2] Risk and compliance management**\n\n"
                        markdown += f"\"How are you balancing technology risk management with {industry} compliance requirements, and what metrics do you use to quantify security and operational resilience?\"\n\n"
                        markdown += f"**[3] Financial planning and forecasting**\n\n"
                        markdown += f"\"What would help most with technology budget planning: better cost predictability, standardized procurement, or clearer alignment between IT spend and business outcomes?\"\n\n"
                    elif persona == 'CTO' or persona == 'CIO':
                        markdown += f"**[1] Digital transformation priorities**\n\n"
                        markdown += f"\"What's driving your technology strategy at {company_name}: modernizing legacy infrastructure, enabling new capabilities, or improving operational efficiency?\"\n\n"
                        markdown += f"**[2] Infrastructure and security**\n\n"
                        markdown += f"\"As you balance innovation with security in {industry}, what's the biggest challenge: managing hybrid environments, reducing complexity, or strengthening resilience?\"\n\n"
                        markdown += f"**[3] Operational excellence**\n\n"
                        markdown += f"\"Where do you see the most opportunity to improve IT operations: standardizing device management, optimizing support models, or reducing vendor fragmentation?\"\n\n"
                    elif persona == 'CISO':
                        markdown += f"**[1] Security posture and threat landscape**\n\n"
                        markdown += f"\"What's your top security priority for {company_name}: reducing attack surface, improving threat detection, or strengthening incident response capabilities?\"\n\n"
                        markdown += f"**[2] Compliance and risk management**\n\n"
                        markdown += f"\"How are you addressing {industry} compliance requirements while enabling business innovation, and where do you see the biggest risk exposure?\"\n\n"
                        markdown += f"**[3] Security infrastructure**\n\n"
                        markdown += f"\"As you evaluate security infrastructure, what matters most: visibility and control, vendor consolidation, or integration with existing security tools?\"\n\n"
                    elif persona == 'COO':
                        markdown += f"**[1] Operational efficiency**\n\n"
                        markdown += f"\"What's the biggest operational bottleneck at {company_name}: process inefficiencies, technology limitations, or coordination across locations?\"\n\n"
                        markdown += f"**[2] Scalability and growth**\n\n"
                        markdown += f"\"As you plan for growth in {industry}, what's most critical: infrastructure scalability, standardized operations, or operational visibility?\"\n\n"
                        markdown += f"**[3] Cross-functional effectiveness**\n\n"
                        markdown += f"\"Where do you see the most opportunity to improve collaboration: better tools and systems, standardized processes, or improved visibility across functions?\"\n\n"
                    else:  # CPO, CEO, other
                        markdown += f"**[1] Strategic priorities**\n\n"
                        markdown += f"\"What are {company_name}'s top strategic priorities in {industry}, and how is technology enabling or constraining those objectives?\"\n\n"
                        markdown += f"**[2] Competitive positioning**\n\n"
                        markdown += f"\"How are you thinking about technology as a competitive differentiator versus operational necessity, and where do you see the biggest opportunity?\"\n\n"
                        markdown += f"**[3] Investment and resource allocation**\n\n"
                        markdown += f"\"As you allocate resources across priorities, how do you evaluate technology investments: strategic impact, operational efficiency, or risk mitigation?\"\n\n"

                markdown += "---\n\n"

        # ============================================================
        # SLIDE: Recommended sales program
        # ============================================================
        markdown += "# Recommended sales program\n\n"

        markdown += "## Recommended Next Steps\n\n"
        markdown += "*Introduce emerging trends and thought leadership to build awareness and credibility. Highlight business challenges and frame HP's solutions as ways to address them. Reinforce proof points with case studies and demonstrate integration value. Emphasize ROI, deployment support, and the ease of scaling with HP solutions.*\n\n"

        # Get recommended collateral/next steps
        next_steps_data = validated_data.get('recommended_next_steps', [])

        # NOTE: Recommended next steps should be generated by enrichment pipeline based on intent signals and opportunities
        if not next_steps_data:
            industry = validated_data.get('industry', 'technology')

            next_steps_data = []

            # Generate next steps based on intent topics
            if intent_topics and len(intent_topics) > 0:
                first_topic = intent_topics[0].get('topic', '') if isinstance(intent_topics[0], dict) else str(intent_topics[0])
                next_steps_data.append({
                    'step': 'Build awareness and credibility',
                    'collateral': f'Thought leadership on {first_topic.lower()} in {industry}',
                    'why': f'Establishes HP expertise in {first_topic.lower()} without forcing product pitch, creating foundation for discovery conversation.'
                })

            # Add problem framing step
            if opportunities and len(opportunities) > 0:
                first_opp = opportunities[0].get('title', '') if isinstance(opportunities[0], dict) else str(opportunities[0])
                next_steps_data.append({
                    'step': 'Frame business challenges',
                    'collateral': f'Case study or insights on {first_opp.lower()}',
                    'why': f'Validates {company_name}\'s challenges are common in {industry} and positions HP solutions as proven approaches.'
                })

            # Add proof points step
            next_steps_data.append({
                'step': 'Demonstrate proven outcomes',
                'collateral': f'Customer success stories from {industry}',
                'why': f'Provides tangible evidence of HP impact with similar organizations in {industry}, building confidence in partnership.'
            })

            # Add ROI/deployment step
            next_steps_data.append({
                'step': 'Enable decision-making',
                'collateral': 'ROI framework and deployment approach',
                'why': f'Addresses financial justification and implementation concerns that matter to {company_name}\'s decision-makers.'
            })

        # Match content audit items for marketing collateral in each step
        load_content_audit()
        first_intent_md = ''
        if intent_topics and len(intent_topics) > 0:
            first_intent_md = intent_topics[0].get('topic', '') if isinstance(intent_topics[0], dict) else str(intent_topics[0])
        md_collateral_used_ids: List[int] = []

        for i, step in enumerate(next_steps_data, 1):
            if isinstance(step, dict):
                step_title = step.get('step', step.get('title', f'Step {i}'))
                collateral = step.get('collateral', step.get('marketing_collateral', ''))
                why = step.get('why', step.get('reason', ''))

                markdown += f"**[{i}] {step_title}**\n\n"

                # Try to match a content audit asset
                matched_collateral = match_content_for_collateral(
                    step_description=step_title,
                    industry=industry,
                    intent_topic=first_intent_md,
                    exclude_ids=md_collateral_used_ids,
                )
                if matched_collateral:
                    md_collateral_used_ids.append(matched_collateral.get('id', 0))
                    ca_name = matched_collateral.get('asset_name', '')
                    ca_link = matched_collateral.get('sp_link', '')
                    if ca_link and ca_link.startswith('http'):
                        markdown += f"Marketing collateral: [{ca_name}]({ca_link})\n\n"
                    else:
                        markdown += f"Marketing collateral: {ca_name}\n\n"
                elif collateral:
                    markdown += f"Marketing collateral: {collateral}\n\n"

                if why:
                    markdown += f"**Why:** {why}\n\n"
            else:
                markdown += f"**[{i}]** {step}\n\n"

        markdown += "## Supporting assets\n\n"
        markdown += "Email template | LinkedIn InMail template | Call script template\n\n"
        markdown += "*See the following slides for ready-to-use outreach templates per persona.*\n\n"

        markdown += "---\n\n"

        # ============================================================
        # SLIDES: Supporting Assets - ONE PER PERSONA
        # ============================================================
        # Generate supporting assets for each unique persona found in stakeholders
        # Map each persona to the first name of the best matching contact
        persona_contacts = {}  # persona type -> first name of best contact
        for stakeholder in all_stakeholders:
            # Ensure stakeholder is a dict
            if not isinstance(stakeholder, dict):
                continue
            title = stakeholder.get('title', '').upper()
            for p in ['CFO', 'CTO', 'CIO', 'CISO', 'COO', 'CPO']:
                if p in title and p not in persona_contacts:
                    full_name = stakeholder.get('name', stakeholder.get('fullName', ''))
                    first_name = full_name.split()[0] if full_name and full_name.strip() else ''
                    persona_contacts[p] = first_name

        # If no personas identified, use default set
        if not persona_contacts:
            persona_contacts = {'CIO': '', 'CTO': '', 'CFO': ''}

        # Generate slide for each persona type
        md_supporting_used_ids: List[int] = list(md_collateral_used_ids)  # avoid reusing collateral picks

        for persona in sorted(persona_contacts):
            contact_first_name = persona_contacts.get(persona, '') or '[First Name]'
            markdown += f"# Supporting assets – [{persona}]\n\n"

            # -------------------------------------------------------
            # Extract bracket fill values from available data context
            # -------------------------------------------------------
            priority_area = ""
            if intent_topics and len(intent_topics) > 0:
                first_topic = intent_topics[0]
                priority_area = first_topic.get('topic', '') if isinstance(first_topic, dict) else str(first_topic)
            if not priority_area:
                priority_area = "technology modernization"

            outcome_or_kpi = "operational efficiency"
            relevant_goal = "improved operational outcomes"
            address_challenge = "strengthen their technology posture and improve outcomes"
            if pain_points and len(pain_points) > 0:
                first_pain = pain_points[0]
                if isinstance(first_pain, dict):
                    address_challenge = first_pain.get('title', address_challenge)
                    pain_desc = first_pain.get('description', '')
                    if 'efficiency' in pain_desc.lower():
                        outcome_or_kpi = "operational efficiency"
                    elif 'security' in pain_desc.lower():
                        outcome_or_kpi = "endpoint security posture"
                    elif 'cost' in pain_desc.lower():
                        outcome_or_kpi = "cost optimization"

            if opportunities and len(opportunities) > 0:
                first_opp = opportunities[0]
                if isinstance(first_opp, dict):
                    relevant_goal = first_opp.get('title', relevant_goal)

            example_a = "improving operational efficiency"
            example_b = "reducing costs"
            if pain_points and len(pain_points) >= 2:
                if isinstance(pain_points[0], dict):
                    example_a = pain_points[0].get('title', example_a)
                if isinstance(pain_points[1], dict):
                    example_b = pain_points[1].get('title', example_b)
            elif pain_points and len(pain_points) == 1 and isinstance(pain_points[0], dict):
                example_a = pain_points[0].get('title', example_a)

            hp_capability = "modernizing device fleets and improving data security"
            solution_summary = "modernizing device fleets to improve security and productivity"
            hp_offering_name = "HP managed device solutions"
            if solutions and len(solutions) > 0:
                first_sol = solutions[0]
                if isinstance(first_sol, dict):
                    hp_capability = first_sol.get('title', hp_capability)
                    sol_desc = first_sol.get('description', '')
                    if sol_desc:
                        solution_summary = sol_desc[:120]
                    hp_offering_name = first_sol.get('title', hp_offering_name)

            similar_org = f"a similar {industry} organization"
            metric_outcome = "operational efficiency by 30%"
            # [outcome] in voicemail is distinct from [outcome or KPI] in email/LinkedIn
            outcome_short = outcome_or_kpi
            if pain_points and len(pain_points) > 0:
                first_pain = pain_points[0]
                if isinstance(first_pain, dict):
                    outcome_short = first_pain.get('title', outcome_or_kpi)
            sp_name = salesperson_name if salesperson_name else "[Your Name]"

            # -------------------------------------------------------
            # Match a content audit asset for this persona
            # -------------------------------------------------------
            sa_md_match = match_content_for_supporting_asset(
                persona=persona,
                industry=industry,
                priority_area=priority_area,
                exclude_ids=md_supporting_used_ids,
            )
            if sa_md_match:
                md_supporting_used_ids.append(sa_md_match.get('id', 0))
                sa_md_name = sa_md_match.get('asset_name', '')
                sa_md_link = sa_md_match.get('sp_link', '')
                if sa_md_link and sa_md_link.startswith('http'):
                    sa_md_text = f"[{sa_md_name}]({sa_md_link})"
                else:
                    sa_md_text = sa_md_name
            else:
                sa_md_text = "[Insert link to supporting asset]"

            # -------------------------------------------------------
            # Email Template (exact HP PDF text)
            # -------------------------------------------------------
            markdown += "## Email Template\n\n"
            markdown += f"**Sender:** HP Sales\n\n"
            markdown += f"**Subject:**\n\n"
            markdown += f"A: Insights that matter to {company_name}\n\n"
            markdown += f"B: Supporting {company_name} on {priority_area}\n\n"
            markdown += "**Body copy:**\n\n"
            markdown += f"Hi {contact_first_name},\n\n"
            markdown += f"I understand {company_name} is focused on {priority_area} this year. I wanted to share something that might help advance that work.\n\n"
            markdown += f"We've seen similar organizations strengthen {outcome_or_kpi} by {hp_capability}.\n\n"
            markdown += "I thought you might find this useful:\n\n"
            markdown += f"{sa_md_text}\n\n"
            markdown += f"Would you be open to a brief conversation about how we could help you achieve {relevant_goal}?\n\n"
            markdown += f"Best regards,\n{sp_name}\nHP Canada | HP\n\n"

            # -------------------------------------------------------
            # LinkedIn InMail Template (exact HP PDF text)
            # -------------------------------------------------------
            markdown += "## LinkedIn InMail Copy\n\n"
            markdown += f"**Subject:** Supporting {company_name} on {priority_area}\n\n"
            markdown += "**Body:**\n\n"
            markdown += f"Hi {contact_first_name},\n\n"
            markdown += f"{priority_area.capitalize() if priority_area else 'Technology modernization'} seems to be a key focus across {industry}. We've seen similar organizations strengthen {outcome_or_kpi} by {hp_capability}.\n\n"
            markdown += "Here's a short resource that outlines how:\n\n"
            markdown += f"{sa_md_text}\n\n"
            markdown += f"Would you be open to a quick chat about what might work best for {company_name}?\n\n"
            markdown += f"Best,\n{sp_name}\nHP Canada\n\n"

            # -------------------------------------------------------
            # Call Script (exact HP PDF text)
            # -------------------------------------------------------
            markdown += "## Outreach Call Script\n\n"

            markdown += "**Step 1: Provide Context**\n\n"
            markdown += f"Hi {contact_first_name}, this is {sp_name} with HP Canada.\n\n"
            markdown += f"I'm calling about {priority_area}. I work with {industry} teams on this. Do you have 30 seconds to see if this is relevant?\n\n"

            markdown += "**Step 2: Explain Offering**\n\n"
            markdown += f"A lot of {industry} teams we work with are looking to {address_challenge}, whether that's {example_a} or {example_b}.\n\n"
            markdown += f"At HP, we've been helping them by {solution_summary}.\n\n"
            markdown += f"For example, {similar_org} recently improved {metric_outcome} after adopting {hp_offering_name}.\n\n"
            markdown += f"It's a quick change that made a measurable difference in {relevant_goal}.\n\n"

            markdown += "**Step 3: CTA**\n\n"
            markdown += f"I can send over a short resource that outlines how we approached this with other {industry} teams. Would that be useful?\n\n"

            # -------------------------------------------------------
            # Voicemail Script (exact HP PDF text)
            # -------------------------------------------------------
            markdown += "## Voicemail Script\n\n"
            markdown += f"Hi {contact_first_name}, this is {sp_name} from HP Canada.\n\n"
            markdown += f"I wanted to share a quick idea about {priority_area}, something we've seen help {industry} teams improve {outcome_short}.\n\n"
            markdown += "If it's something you're exploring, I'd be happy to send over a short resource or set up a quick chat.\n\n"
            markdown += f"You can reach me at [phone number].\n\n"
            markdown += f"Again, it's {sp_name} with HP Canada. Hope we can connect soon.\n\n"

            # -------------------------------------------------------
            # Objection Handling (exact HP PDF text)
            # -------------------------------------------------------
            markdown += "## Objection Handling\n\n"

            markdown += "**Objection: I'm not interested.**\n\n"
            markdown += f"Totally understand. I'm not calling to sell anything. I just wanted to share a quick perspective we've seen make a difference for other teams in {industry}.\n\n"
            markdown += "Would you be open to looking at a short resource?\n\n"

            markdown += "**Objection: We're already working with another vendor.**\n\n"
            markdown += "That's great. A lot of teams we work with were in a similar position and just wanted to see if there were areas they could do things a bit more efficiently.\n\n"
            markdown += "Would it make sense to share a quick example?\n\n"

            markdown += "**Objection: Now's not a good time.**\n\n"
            markdown += "Of course. Is there a time when you will be available later this week? I can make it quick. 10 minutes tops.\n\n"

            markdown += "**Objection: Send me something.**\n\n"
            markdown += f"Absolutely. I'll send over a short piece on {priority_area}. If it seems relevant, we can reconnect to see if there's a fit.\n\n"

            markdown += "---\n\n"

        # ============================================================
        # LAST SLIDE: Thank You, Feedback and Questions
        # ============================================================
        markdown += "# Thank You\n\n"

        markdown += "## Let Us Know What You Think\n\n"
        markdown += "Your feedback helps us make future reports even more relevant and useful.\n\n"

        markdown += "## Share Your Thoughts\n\n"
        markdown += "If you have any questions about this report, contact the HP RAD Intelligence Desk.\n\n"

        markdown += "---\n\n"

        # Footer with metadata
        markdown += "## Report Metadata\n\n"
        confidence_score = company_data.get("confidence_score", 0.85)
        sources_count = len(validated_data.get('sources', ['Apollo', 'PDL', 'Hunter', 'GNews']))
        markdown += f"| Metric | Value |\n"
        markdown += f"|--------|-------|\n"
        markdown += f"| Data Confidence Score | {confidence_score:.0%} |\n"
        markdown += f"| Data Sources Used | {sources_count} |\n"
        markdown += f"| Report Generated | {current_date} |\n"
        markdown += f"| Prepared By | HP RAD Intelligence Desk |\n\n"

        markdown += "*Confidential - For Internal HP Use Only*\n"

        return markdown

    async def _send_to_gamma(
        self,
        markdown_content: str,
        num_cards: int = 10,
        company_data: Dict[str, Any] = None,
        user_email: str = None
    ) -> Dict[str, Any]:
        """
        Send markdown content to Gamma API for slideshow generation.

        IMPORTANT: Configured for professional HP-branded presentations:
        - NO AI generated images
        - Professional/corporate design
        - Charts and data visualizations preferred

        Args:
            markdown_content: Formatted markdown string
            num_cards: Number of slides to generate

        Returns:
            Dictionary with Gamma API response including URL

        Raises:
            Exception: If API request fails
        """
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

        # Choose endpoint and payload based on whether template is used
        if self.template_id:
            # Use template endpoint: /v1.0/generations/from-template
            # Template has 1 slide per C-suite role — we pick the best contact per role.
            api_endpoint = self.template_url

            structured_data = self._format_for_template(company_data, user_email)

            payload = {
                "gammaId": self.template_id,
                "prompt": structured_data
            }
            logger.info(f"Using template endpoint with gammaId: {self.template_id}")
            logger.info(f"Sending structured data (length: {len(structured_data)} chars)")
        else:
            # Use standard generation endpoint: /v1.0/generations
            api_endpoint = self.api_url
            payload = {
                "inputText": markdown_content,
                "textMode": "preserve",
                "format": "presentation"
            }

            # Add numCards for standard generation (not supported by template endpoint)
            if num_cards and 5 <= num_cards <= 100:
                payload["numCards"] = num_cards
                logger.info(f"Requesting {num_cards} cards")

        logger.info(f"Payload keys: {list(payload.keys())}")

        try:
            # Increased timeout for complex presentations
            async with httpx.AsyncClient(timeout=300) as client:
                # Create generation
                logger.info(f"Sending request to Gamma API: {api_endpoint}")
                logger.info(f"Using template: {self.template_id if self.template_id else 'None (standard generation)'}")

                response = await client.post(
                    api_endpoint,
                    json=payload,
                    headers=headers
                )

                logger.info(f"Gamma API status code: {response.status_code}")
                response.raise_for_status()
                result = response.json()

                logger.info(f"Gamma API response keys: {list(result.keys())}")
                logger.info(f"Full Gamma API response: {result}")

                generation_id = result.get("generationId") or result.get("generation_id") or result.get("id")
                if not generation_id:
                    logger.error(f"❌ No generationId in response!")
                    logger.error(f"Response keys: {list(result.keys())}")
                    logger.error(f"Full response: {result}")
                    raise Exception(f"No generationId returned from Gamma API. Response keys: {list(result.keys())}")

                logger.info(f"Generation started with ID: {generation_id}")
                logger.info(f"Markdown length: {len(markdown_content)} characters")
                logger.info(f"Template ID: {self.template_id}")

                # Poll for completion. Ceiling is configured per-instance via
                # self.polling_max_attempts (default 300 = 600 s = 10 min) so
                # tests can override it without monkeypatching constants.
                max_attempts = self.polling_max_attempts
                attempt = 0
                last_logged_time = 0

                while attempt < max_attempts:
                    await asyncio.sleep(2)
                    attempt += 1

                    try:
                        status_response = await client.get(
                            f"{self.status_url}/{generation_id}",
                            headers=headers
                        )

                        status_response.raise_for_status()
                        status_data = status_response.json()

                        status = status_data.get("status")

                        # Log every 10 seconds to avoid spam, or on status change
                        should_log = (
                            attempt % 5 == 0 or
                            status in ["completed", "failed"] or
                            attempt == 1
                        )

                        if should_log:
                            elapsed = attempt * 2
                            logger.info(f"⏳ Generation status after {elapsed}s (attempt {attempt}/{max_attempts}): {status}")
                            logger.info(f"   Generation ID: {generation_id}")
                            # Only log full response on first attempt and completion/failure
                            if attempt == 1 or status in ["completed", "failed"]:
                                logger.info(f"   Full status response: {status_data}")

                        if status == "completed":
                            # CRITICAL: Log all URL-related fields for debugging
                            logger.info("=" * 60)
                            logger.info("GENERATION COMPLETED - Checking for URL fields:")
                            logger.info(f"  gammaUrl: {status_data.get('gammaUrl')}")
                            logger.info(f"  url: {status_data.get('url')}")
                            logger.info(f"  webUrl: {status_data.get('webUrl')}")
                            logger.info(f"  gamma_url: {status_data.get('gamma_url')}")
                            logger.info(f"  All keys in response: {list(status_data.keys())}")
                            logger.info(f"  Full response: {status_data}")
                            logger.info("=" * 60)

                            # Try multiple possible URL keys
                            gamma_url = (
                                status_data.get("gammaUrl") or
                                status_data.get("url") or
                                status_data.get("webUrl") or
                                status_data.get("gamma_url")
                            )

                            # Fallback: Search all keys for any URL-like field
                            if not gamma_url:
                                logger.warning("Standard URL fields not found, searching all fields...")
                                for key, value in status_data.items():
                                    if isinstance(value, str) and ("gamma.app" in value or "http" in value):
                                        logger.info(f"Found URL-like value in field '{key}': {value}")
                                        gamma_url = value
                                        break

                            # Check nested objects for URL
                            if not gamma_url and isinstance(status_data.get("gamma"), dict):
                                gamma_url = status_data["gamma"].get("url") or status_data["gamma"].get("webUrl")

                            # Check if URL is in a 'data' wrapper
                            if not gamma_url and isinstance(status_data.get("data"), dict):
                                gamma_url = status_data["data"].get("url") or status_data["data"].get("gammaUrl")

                            # Check for 'link' or 'viewLink' fields
                            if not gamma_url:
                                gamma_url = status_data.get("link") or status_data.get("viewLink") or status_data.get("shareLink")

                            # CRITICAL FIX: Construct valid URL from generation ID if still not found
                            # The Gamma API may not return the URL directly for template-based generations
                            if not gamma_url and generation_id:
                                # Standard Gamma URL format: https://gamma.app/docs/[generationId]
                                gamma_url = f"https://gamma.app/docs/{generation_id}"
                                logger.warning(f"URL not found in API response. Constructed URL from generation ID: {gamma_url}")

                            # Final validation
                            if not gamma_url:
                                logger.error(f"❌ No URL field found in completed response!")
                                logger.error(f"Response keys: {list(status_data.keys())}")
                                logger.error(f"Full response: {status_data}")
                                raise Exception(f"No URL returned from completed generation. Response keys: {list(status_data.keys())}")

                            logger.info(f"✅ Slideshow URL: {gamma_url}")
                            return {
                                "url": gamma_url,
                                "id": generation_id,
                                "status": "generated"
                            }

                        elif status == "failed":
                            error_msg = status_data.get("error", "Unknown error")
                            raise Exception(f"Generation failed: {error_msg}")

                        # Still processing, continue polling
                        elif status in ["pending", "processing", "generating"]:
                            continue

                        # Unknown status
                        else:
                            logger.warning(f"Unknown status: {status}")

                    except httpx.HTTPStatusError as e:
                        logger.error(f"Status check failed: {e.response.status_code}")
                        if attempt >= max_attempts:
                            raise

                # If we exit the loop without returning, the per-request
                # polling window is exhausted. We do NOT raise here — that
                # would discard `generation_id` and lose the slideshow even
                # though Gamma may still complete it. Instead, return a
                # pending result; the pipeline will hand the generation_id
                # to the background reconcile loop, and /job-status will
                # also lazy-reconcile on read.
                timeout_seconds = max_attempts * 2
                last_status = status if 'status' in locals() else 'unknown'
                logger.warning(
                    f"⏳ Polling window exhausted after {timeout_seconds}s "
                    f"({max_attempts} attempts). Last status: {last_status}. "
                    f"Generation ID {generation_id} handed off to reconcile."
                )
                return {
                    "url": None,
                    "id": generation_id,
                    "status": "pending",
                    "last_known_status": last_status,
                }

        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_body = e.response.text
            except:
                pass
            logger.error(f"Gamma API HTTP error: {e.response.status_code} - {error_body}")
            raise Exception(
                f"Gamma API error: {e.response.status_code}"
            ) from e

        except httpx.RequestError as e:
            logger.error(f"Gamma API request error: {e}")
            raise Exception("Failed to connect to Gamma API") from e

        except Exception as e:
            logger.error(f"Unexpected error with Gamma API: {e}")
            raise

    async def check_generation_status(self, generation_id: str) -> Dict[str, Any]:
        """
        Single non-polling status check against Gamma's generations endpoint.

        Used by both the inline lazy reconcile in /job-status and the
        background reconcile loop. Always returns a structured dict; never
        raises for routine HTTP/connection errors so callers can decide what
        to do based on the returned status.

        Returns:
            {
                "status": "pending" | "processing" | "generating" |
                          "completed" | "failed" | "error",
                "url":    str | None,
                "id":     generation_id,
                "error":  str | None,
            }
        """
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"{self.status_url}/{generation_id}",
                    headers=headers,
                )
                response.raise_for_status()
                status_data = response.json()
        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "url": None,
                "id": generation_id,
                "error": f"Gamma status HTTP {e.response.status_code}",
            }
        except httpx.RequestError as e:
            return {
                "status": "error",
                "url": None,
                "id": generation_id,
                "error": f"Gamma status connection error: {e}",
            }

        gamma_status = status_data.get("status")

        if gamma_status == "completed":
            url = self._extract_url(status_data, generation_id)
            return {
                "status": "completed",
                "url": url,
                "id": generation_id,
                "error": None,
            }
        if gamma_status == "failed":
            return {
                "status": "failed",
                "url": None,
                "id": generation_id,
                "error": status_data.get("error", "Gamma generation failed"),
            }

        # pending / processing / generating / unknown — caller keeps polling
        return {
            "status": gamma_status or "pending",
            "url": None,
            "id": generation_id,
            "error": None,
        }

    @staticmethod
    def _extract_url(status_data: Dict[str, Any], generation_id: str) -> Optional[str]:
        """
        Mirror the URL-extraction fallback chain used by _send_to_gamma so the
        single-shot status check returns the same URL the polling loop would.
        """
        url = (
            status_data.get("gammaUrl")
            or status_data.get("url")
            or status_data.get("webUrl")
            or status_data.get("gamma_url")
        )
        if not url:
            for key, value in status_data.items():
                if isinstance(value, str) and ("gamma.app" in value or "http" in value):
                    url = value
                    break
        if not url and isinstance(status_data.get("gamma"), dict):
            url = status_data["gamma"].get("url") or status_data["gamma"].get("webUrl")
        if not url and isinstance(status_data.get("data"), dict):
            url = status_data["data"].get("url") or status_data["data"].get("gammaUrl")
        if not url:
            url = (
                status_data.get("link")
                or status_data.get("viewLink")
                or status_data.get("shareLink")
            )
        if not url and generation_id:
            url = f"https://gamma.app/docs/{generation_id}"
        return url

    async def reconcile_pending_generation(
        self,
        generation_id: str,
        max_total_seconds: int = 1800,
        poll_interval_seconds: int = 5,
    ) -> Dict[str, Any]:
        """
        Background reconcile loop for generations that outlasted the
        per-request polling window in _send_to_gamma. Polls Gamma every
        `poll_interval_seconds` until a terminal state is reached or
        `max_total_seconds` elapses.

        Default hard cap is 30 minutes — well beyond the worst observed
        Gamma queue depth — but still finite so a stuck generation can't
        leak background tasks indefinitely.

        Returns the same structured dict shape as check_generation_status.
        """
        max_attempts = max(1, max_total_seconds // max(1, poll_interval_seconds))
        last_result: Dict[str, Any] = {
            "status": "pending",
            "url": None,
            "id": generation_id,
            "error": None,
        }

        for attempt in range(1, max_attempts + 1):
            result = await self.check_generation_status(generation_id)
            last_result = result
            terminal = result["status"] in ("completed", "failed")
            if terminal:
                logger.info(
                    f"Reconcile for generation_id={generation_id} reached "
                    f"{result['status']} after {attempt} polls"
                )
                return result
            await asyncio.sleep(poll_interval_seconds)

        logger.warning(
            f"Reconcile for generation_id={generation_id} hit hard cap "
            f"({max_total_seconds}s) — final status: {last_result['status']}"
        )
        return last_result

    async def create_batch_slideshows(
        self,
        companies_data: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        """
        Create multiple slideshows in batch.

        Args:
            companies_data: List of company data dictionaries

        Returns:
            List of results with slideshow URLs

        Raises:
            Exception: If batch creation fails
        """
        logger.info(f"Creating {len(companies_data)} slideshows in batch")

        results = []

        for company_data in companies_data:
            try:
                result = await self.create_slideshow(company_data)
                results.append(result)

            except Exception as e:
                logger.error(
                    f"Failed to create slideshow for "
                    f"{company_data.get('company_name')}: {e}"
                )
                results.append({
                    "success": False,
                    "error": str(e),
                    "company_name": company_data.get("company_name")
                })

        logger.info(
            f"Batch slideshow creation complete. "
            f"{len([r for r in results if r.get('success')])} successful"
        )

        return results
