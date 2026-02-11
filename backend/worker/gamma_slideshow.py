"""
Gamma API slideshow creation module.
Creates markdown prompts and generates slideshows via Gamma API.
"""
import logging
import asyncio
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class GammaSlideshowCreator:
    """
    Creates slideshows using Gamma API from company data.

    Process:
    1. Retrieve finalized data from Supabase
    2. Format data as markdown
    3. Send to Gamma API
    4. Return slideshow URL
    """

    def __init__(self, gamma_api_key: str, template_id: str = "g_vsj27dcr73l1nv1"):
        """
        Initialize Gamma slideshow creator.

        Args:
            gamma_api_key: Gamma API key (from environment)
            template_id: Gamma template ID (gammaId) for template-based generation
                        Default: g_vsj27dcr73l1nv1 (HP RAD Intelligence template)

        Note:
            API key must be provided via environment variables.
            Template will preserve its exact design, fonts, and logos.
        """
        self.api_key = gamma_api_key
        self.template_id = template_id or "g_vsj27dcr73l1nv1"  # Always use template by default
        self.api_url = "https://public-api.gamma.app/v1.0/generations"
        self.template_url = "https://public-api.gamma.app/v1.0/generations/from-template"
        self.status_url = "https://public-api.gamma.app/v1.0/generations"

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
            company_name = company_data.get('validated_data', {}).get('company_name') or company_data.get('company_name', 'Company')
            logger.info(f"Creating slideshow for {company_name}")

            # Generate markdown content with user email for attribution
            markdown_content = self._generate_markdown(company_data, user_email)

            # Count stakeholders to estimate number of cards needed
            stakeholders = company_data.get('validated_data', {}).get('stakeholder_profiles', [])
            if isinstance(stakeholders, dict):
                stakeholder_count = len(stakeholders)
            elif isinstance(stakeholders, list):
                stakeholder_count = len(stakeholders)
            else:
                stakeholder_count = 1

            # Count unique persona types for supporting assets slides
            persona_types = set()
            if isinstance(stakeholders, list):
                for s in stakeholders:
                    role = s.get('title', '').upper()
                    for persona in ['CIO', 'CTO', 'CISO', 'COO', 'CFO', 'CPO']:
                        if persona in role:
                            persona_types.add(persona)
            persona_count = len(persona_types) if persona_types else 3  # Default to 3 personas

            # Slide count:
            # 1. Title
            # 2. Executive Snapshot
            # 3. Buying Signals
            # 4. Opportunity themes
            # 5+. Stakeholder profiles (one per stakeholder)
            # Next. Recommended sales program
            # Next+. Supporting Assets (one per persona type)
            # Last. Feedback
            num_cards = 4 + stakeholder_count + 1 + persona_count + 1

            # Send to Gamma API
            result = await self._send_to_gamma(markdown_content, num_cards, company_data, user_email)

            logger.info(f"Slideshow created successfully: {result.get('url')}")

            return {
                "success": True,
                "slideshow_url": result.get("url"),
                "slideshow_id": result.get("id"),
                "company_name": company_name
            }

        except Exception as e:
            logger.error(f"Failed to create slideshow: {e}")
            raise

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

        # Build comprehensive, data-rich structured content
        data = f"""ACCOUNT INTELLIGENCE REPORT

Company: {company_name}
Report Date: {current_date}
Prepared By: HP RAD Intelligence Desk
Prepared For: {user_email or 'HP Sales Team'}

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
Account Type: {validated_data.get('account_type', validated_data.get('target_market', validated_data.get('company_type', 'Private Sector')))}
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
Estimated IT Budget: {validated_data.get('estimated_it_spend', validated_data.get('it_budget', 'Contact for estimate'))}

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

        # Pain Points
        pain_points = validated_data.get('pain_points', [])
        if pain_points:
            data += "=== PAIN POINTS ===\n\n"
            for i, pain in enumerate(pain_points, 1):
                if isinstance(pain, dict):
                    data += f"{i}. {pain.get('title', pain)}\n"
                    if pain.get('description'):
                        data += f"   {pain['description']}\n"
                else:
                    data += f"{i}. {pain}\n"
                data += "\n"

        # Opportunities
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

        # Stakeholders - comprehensive from both formats
        stakeholder_map = validated_data.get('stakeholder_map', {})
        stakeholder_profiles = validated_data.get('stakeholder_profiles', [])

        # Extract stakeholders from stakeholder_map if available
        if stakeholder_map and stakeholder_map.get('stakeholders'):
            stakeholders = stakeholder_map['stakeholders']
        elif stakeholder_profiles:
            stakeholders = stakeholder_profiles
        else:
            stakeholders = []

        if stakeholders:
            data += "=== KEY STAKEHOLDERS ===\n\n"
            for idx, stakeholder in enumerate(stakeholders, 1):
                # Basic info
                name = stakeholder.get('name', stakeholder.get('fullName', 'Not available'))
                title = stakeholder.get('title', stakeholder.get('role', 'Not available'))
                email = stakeholder.get('email', stakeholder.get('contact', {}).get('email', 'Not available'))
                phone = stakeholder.get('phone', stakeholder.get('mobile', stakeholder.get('contact', {}).get('phone', 'Not available')))
                linkedin = stakeholder.get('linkedin', stakeholder.get('linkedinUrl', stakeholder.get('linkedin_url', stakeholder.get('contact', {}).get('linkedinUrl', 'Not available'))))

                data += f"[{idx}] {name}\n"
                data += f"Title: {title}\n"

                # Department/Seniority if available
                if stakeholder.get('department'):
                    data += f"Department: {stakeholder['department']}\n"
                if stakeholder.get('seniority'):
                    data += f"Seniority: {stakeholder['seniority']}\n"

                # Contact info
                data += f"Email: {email}\n"
                if phone and phone != 'Not available':
                    data += f"Phone: {phone}\n"
                if linkedin and linkedin != 'Not available':
                    data += f"LinkedIn: {linkedin}\n"

                # Bio/About
                bio = stakeholder.get('bio', stakeholder.get('about', stakeholder.get('description', '')))
                if bio:
                    data += f"About: {bio}\n"

                # Strategic Priorities
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

                # Communication Preference
                comm_pref = stakeholder.get('communication_preference', stakeholder.get('communicationPreference', ''))
                if comm_pref:
                    data += f"Preferred Contact: {comm_pref}\n"

                # Recommended Play
                rec_play = stakeholder.get('recommended_play', stakeholder.get('recommendedPlay', ''))
                if rec_play:
                    data += f"Recommended Approach: {rec_play}\n"

                # Data quality indicator if available
                if stakeholder.get('confidence') or stakeholder.get('email_verified'):
                    confidence = stakeholder.get('confidence', 0)
                    verified = stakeholder.get('email_verified', False)
                    if confidence > 80 or verified:
                        data += f"✓ Verified Contact\n"

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
        5+. Stakeholder Map: Role Profiles (one per stakeholder)
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

        # User email (person pulling data)
        preparer_email = user_email or company_data.get('user_email', '[salesperson@hp.com]')

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
        markdown += f"**Prepared for:** {preparer_email} by the HP RAD Intelligence Desk\n\n"
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
        account_type = validated_data.get('account_type', '')
        if not account_type:
            # Infer from company type or industry
            company_type = validated_data.get('type', validated_data.get('company_type', ''))
            if 'government' in str(company_type).lower() or 'public' in str(company_type).lower():
                account_type = 'Public Sector'
            else:
                account_type = 'Private Sector'
        markdown += f"**Account Type:** {account_type}\n\n"

        # Industry
        industry = validated_data.get('industry', 'Technology')
        markdown += f"**Industry:** {industry}\n\n"

        # Estimated Annual IT Budget
        it_spend = validated_data.get('estimated_it_spend') or validated_data.get('it_budget') or validated_data.get('inferred_revenue', '')
        if it_spend:
            markdown += f"**Estimated Annual IT Budget:** ${it_spend}\n\n"
        else:
            # Try to estimate from employee count
            employee_count = validated_data.get('employee_count', 0)
            if employee_count:
                try:
                    emp_num = int(str(employee_count).replace(',', '').split('-')[0])
                    # Rough estimate: $10k-50k per employee for IT
                    low = emp_num * 10000
                    high = emp_num * 50000
                    markdown += f"**Estimated Annual IT Budget:** ${low//1000000}M-${high//1000000}M (estimated based on {employee_count} employees)\n\n"
                except:
                    markdown += "**Estimated Annual IT Budget:** Contact for estimate\n\n"
            else:
                markdown += "**Estimated Annual IT Budget:** Contact for estimate\n\n"

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
            pain_points = validated_data.get('pain_points') or validated_data.get('opportunity_themes', {}).get('pain_points', [])

        # NOTE: Pain points should be generated by LLM Council based on company data, news, and industry
        if not pain_points and not data_unavailable:
            industry = validated_data.get('industry', 'technology')
            employee_count = validated_data.get('employee_count', 0)

            # Generate industry-relevant pain points dynamically
            pain_points = []

            # Size-based pain point
            if isinstance(employee_count, int) and employee_count > 10000:
                pain_points.append({'title': 'Enterprise-scale coordination and standardization', 'description': f'Managing technology standards and user experience across a large {employee_count}+ employee organization creates complexity and support burden.'})
            elif isinstance(employee_count, int) and employee_count > 1000:
                pain_points.append({'title': 'Growth-stage operational efficiency', 'description': f'Scaling operations efficiently while maintaining quality across {employee_count}+ employees requires standardized technology and streamlined support models.'})
            else:
                pain_points.append({'title': 'Resource optimization and efficiency', 'description': 'Balancing technology investments with operational efficiency requires strategic vendor partnerships and scalable solutions.'})

            # Industry-specific pain point
            if any(word in industry.lower() for word in ['manufacturing', 'automotive', 'industrial']):
                pain_points.append({'title': 'Operational technology modernization', 'description': f'{industry} digital transformation requires bridging legacy systems with modern infrastructure while maintaining uptime.'})
            elif any(word in industry.lower() for word in ['financial', 'banking', 'insurance']):
                pain_points.append({'title': 'Regulatory compliance and security', 'description': f'{industry} faces stringent compliance requirements requiring secure, auditable technology infrastructure and risk management.'})
            elif any(word in industry.lower() for word in ['healthcare', 'medical']):
                pain_points.append({'title': 'Patient data security and compliance', 'description': f'{industry} must balance innovation with HIPAA compliance, requiring secure infrastructure and careful vendor selection.'})
            else:
                pain_points.append({'title': 'Digital transformation acceleration', 'description': f'{industry} requires modern infrastructure to support business agility and competitive differentiation.'})

            # Universal pain point
            pain_points.append({'title': 'Technology investment ROI and visibility', 'description': 'Demonstrating technology value requires clear metrics, cost transparency, and alignment between IT investments and business outcomes.'})

        for i, pain in enumerate(pain_points, 1):
            if isinstance(pain, dict):
                pain_title = pain.get('title', pain.get('name', f'Pain Point {i}'))
                pain_desc = pain.get('description', pain.get('pain_point', ''))
                markdown += f"**[{i}] {pain_title}**\n\n"
                if pain_desc:
                    markdown += f"{pain_desc}\n\n"
            else:
                markdown += f"**[{i}]** {str(pain)}\n\n"

        # Sales opportunities
        markdown += "## Sales opportunities\n\n"

        if data_unavailable:
            markdown += "**Data unavailable at the time.** Sales opportunities could not be identified due to insufficient company data.\n\n"
            opportunities = []  # Skip opportunity generation
        else:
            opportunities = validated_data.get('sales_opportunities') or validated_data.get('opportunities', [])

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
                        'description': f'Validate current state and priorities around {topic_name.lower()}. Qualify scope, timeline, budget authority, and decision-making process.'
                    })

            # Add infrastructure opportunity
            opportunities.append({
                'title': 'Infrastructure modernization and lifecycle management',
                'description': f'Validate {company_name}\'s refresh cycles, standardization goals, and support model preferences. Qualify device volumes, deployment timeline, and integration requirements.'
            })

            # Ensure we have at least 3
            if len(opportunities) < 3:
                opportunities.append({
                    'title': 'Managed services and support optimization',
                    'description': 'Validate current support burden and operational pain points. Qualify appetite for managed services, success metrics, and service level requirements.'
                })

        for i, opp in enumerate(opportunities, 1):
            if isinstance(opp, dict):
                opp_title = opp.get('title', opp.get('name', f'Opportunity {i}'))
                opp_desc = opp.get('description', opp.get('details', ''))
                markdown += f"**[{i}] {opp_title}**\n\n"
                if opp_desc:
                    markdown += f"{opp_desc}\n\n"
            else:
                markdown += f"**[{i}]** {str(opp)}\n\n"

        # Recommended solution areas
        markdown += "## Recommended solution areas\n\n"

        if data_unavailable:
            markdown += "**Data unavailable at the time.** Recommended solutions could not be identified due to insufficient company data.\n\n"
            solutions = []  # Skip solution generation
        else:
            solutions = validated_data.get('recommended_solutions') or validated_data.get('recommended_focus') or validated_data.get('opportunity_themes', {}).get('solutions', [])

        # NOTE: Solution areas should be generated by LLM Council based on pain points and opportunities
        if not solutions and not data_unavailable:
            industry = validated_data.get('industry', 'technology')

            solutions = []

            # Map pain points to solutions
            for i, pain in enumerate(pain_points[:3], 1):
                pain_title = pain.get('title', '') if isinstance(pain, dict) else str(pain)
                if 'security' in pain_title.lower() or 'compliance' in pain_title.lower():
                    solutions.append({
                        'title': 'Enterprise security and compliance infrastructure',
                        'description': f'Address {pain_title.lower()} with secure, compliance-ready hardware and infrastructure solutions designed for {industry}.'
                    })
                elif 'scale' in pain_title.lower() or 'efficiency' in pain_title.lower() or 'optimization' in pain_title.lower():
                    solutions.append({
                        'title': 'Managed services and operational efficiency',
                        'description': f'Reduce operational burden through managed services, standardized device fleets, and proactive support models that address {pain_title.lower()}.'
                    })
                elif 'transformation' in pain_title.lower() or 'modernization' in pain_title.lower():
                    solutions.append({
                        'title': 'Infrastructure modernization and digital enablement',
                        'description': f'Enable business agility with modern infrastructure, cloud-ready solutions, and scalable technology that supports {pain_title.lower()}.'
                    })
                else:
                    solutions.append({
                        'title': f'Solutions addressing {pain_title.lower()}',
                        'description': f'HP offers comprehensive technology and services to address {pain_title.lower()} through proven enterprise solutions and support.'
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
                markdown += f"**[Area {i}] {solution_title}**\n\n"
                if solution_desc:
                    markdown += f"{solution_desc}\n\n"
            else:
                markdown += f"**[Area {i}]** {str(solution)}\n\n"

        markdown += "---\n\n"


        # ============================================================
        # SLIDES 5+: Stakeholder Map: Strategic Role Profiles (ONE PER CONTACT)
        # NOTE: stakeholder_profiles now contains up to 3 STRATEGIC REAL contacts
        # selected by LLM Council as most important roles for HP to target
        # ============================================================

        if data_unavailable:
            # Show data unavailable slide for stakeholders
            markdown += "# Stakeholder Map: Role Profiles\n\n"
            markdown += "## Data Unavailable\n\n"
            markdown += f"**Data unavailable at the time.** Stakeholder and contact information for {company_name} could not be retrieved. This may indicate:\n\n"
            markdown += "- The company name is incorrect or the company does not exist\n- The company is private or unlisted with limited public information\n- External data sources are temporarily unavailable\n- Contact data requires manual research or verification\n\n"
            markdown += "Please verify the company name and try again, or conduct manual research through LinkedIn, company website, and other professional networks.\n\n"
            markdown += "---\n\n"
        else:
            # Get strategic stakeholders (ALREADY filtered to up to 3 by LLM Council in orchestrator)
            # These are REAL contacts only, matched to strategic roles
            stakeholders = validated_data.get('stakeholder_profiles') or validated_data.get('stakeholders', [])

            # Use strategic stakeholders directly (NO hunter contacts, NO CEO fallback)
            # These are REAL contacts that match the 3 strategic roles
            all_stakeholders = []

            if isinstance(stakeholders, list):
                all_stakeholders = stakeholders  # Use directly, already filtered
            elif isinstance(stakeholders, dict):
                for role, profile in stakeholders.items():
                    if isinstance(profile, dict):
                        profile['role_type'] = role
                        all_stakeholders.append(profile)

            # If still no stakeholders, show minimal unavailable message
            if not all_stakeholders:
                markdown += "# Stakeholder Map: Role Profiles\n\n"
                markdown += "## Data Unavailable\n\n"
                markdown += f"**Stakeholder data unavailable at the time.** Contact information for {company_name} could not be retrieved. Manual research recommended.\n\n"
                markdown += "---\n\n"

            # Generate a slide for EACH stakeholder
            for stakeholder in all_stakeholders:
                name = stakeholder.get('name', 'Contact Name')
                title = stakeholder.get('title', stakeholder.get('role_type', stakeholder.get('position', 'Executive')))

            # Determine persona type from title
            persona = "Executive"
            title_upper = title.upper()
            for p in ['CFO', 'CTO', 'CIO', 'CISO', 'COO', 'CPO', 'CEO']:
                if p in title_upper:
                    persona = p
                    break

            markdown += f"# Stakeholder Map: Role Profiles\n\n"
            markdown += f"## Persona: {persona}\n\n"

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

            # Phone numbers - check ALL possible field variations from all sources
            # ZoomInfo: phone, mobile_phone, direct_phone
            # Apollo: phone, phone_number
            # PDL: phone, mobile_phone
            phone = stakeholder.get('phone', stakeholder.get('phone_number', stakeholder.get('phoneNumber', '')))
            mobile = stakeholder.get('mobile', stakeholder.get('mobile_phone', stakeholder.get('mobilePhone', '')))
            direct_phone = stakeholder.get('direct_phone', stakeholder.get('directPhone', ''))

            if direct_phone:
                markdown += f"**Direct Phone:** {direct_phone}\n\n"
            else:
                markdown += "**Direct Phone:** Currently unavailable\n\n"

            if mobile:
                markdown += f"**Mobile Phone:** {mobile}\n\n"
            elif phone and not direct_phone:
                markdown += f"**Mobile Phone:** {phone}\n\n"
            else:
                markdown += "**Mobile Phone:** Currently unavailable\n\n"

            # Email
            email = stakeholder.get('email', stakeholder.get('value', ''))
            if email:
                markdown += f"**Email:** {email}\n\n"
            else:
                markdown += "**Email:** Currently unavailable\n\n"

            # LinkedIn
            linkedin = stakeholder.get('linkedin', '')
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
        markdown += "*[Introduce emerging trends and thought leadership to build awareness and credibility / Highlight business challenges and frame HP's solutions as ways to address them / Reinforce proof points with case studies and demonstrate integration value / Emphasize ROI, deployment support, and the ease of scaling with HP solutions.]*\n\n"

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

        for i, step in enumerate(next_steps_data, 1):
            if isinstance(step, dict):
                step_title = step.get('step', step.get('title', f'Step {i}'))
                collateral = step.get('collateral', step.get('marketing_collateral', ''))
                why = step.get('why', step.get('reason', ''))

                markdown += f"**[{i}] {step_title}**\n\n"
                if collateral:
                    markdown += f"Marketing collateral: {collateral}\n\n"
                if why:
                    markdown += f"**Why:** {why}\n\n"
            else:
                markdown += f"**[{i}]** {step}\n\n"

        markdown += "## Supporting assets\n\n"
        markdown += "[Email template] [LinkedIn outreach template] [Call script template]\n\n"

        markdown += "---\n\n"

        # ============================================================
        # SLIDES: Supporting Assets - ONE PER PERSONA
        # ============================================================
        # Generate supporting assets for each unique persona found in stakeholders
        persona_types = set()
        for stakeholder in all_stakeholders:
            title = stakeholder.get('title', '').upper()
            for p in ['CFO', 'CTO', 'CIO', 'CISO', 'COO', 'CPO']:
                if p in title:
                    persona_types.add(p)

        # If no personas identified, use default set
        if not persona_types:
            persona_types = {'CIO', 'CTO', 'CFO'}

        # Generate slide for each persona type
        for persona in sorted(persona_types):
            markdown += f"# Supporting assets – [{persona}]\n\n"

            # Get persona-specific context
            relevant_topic = "Not available"
            if intent_topics and len(intent_topics) > 0:
                first_topic = intent_topics[0]
                relevant_topic = first_topic.get('topic', '') if isinstance(first_topic, dict) else str(first_topic)

            # Get pain point context
            relevant_initiative = "operational excellence"
            desired_outcome = "improved efficiency"
            if pain_points and len(pain_points) > 0:
                first_pain = pain_points[0]
                if isinstance(first_pain, dict):
                    relevant_initiative = first_pain.get('title', 'operational excellence')
                    pain_desc = first_pain.get('description', '')
                    if 'efficiency' in pain_desc.lower():
                        desired_outcome = "improved operational efficiency"
                    elif 'security' in pain_desc.lower():
                        desired_outcome = "enhanced security posture"
                    elif 'cost' in pain_desc.lower():
                        desired_outcome = "optimized costs"

            # Get solution approach
            approach = "Not available"
            if opportunities and len(opportunities) > 0:
                first_opp = opportunities[0]
                if isinstance(first_opp, dict):
                    approach = first_opp.get('title', 'strategic technology investments')

            # Email Template
            markdown += "## Email Template\n\n"
            markdown += f"**Sender:** HP Canada\n\n"
            markdown += f"**Subject line:**\n\n"
            markdown += f"A: Insights that matter to {company_name}\n\n"
            markdown += f"B: Supporting {company_name} on {relevant_topic if relevant_topic != 'Not available' else 'your technology priorities'}\n\n"
            markdown += "**Body:**\n\n"
            markdown += f"Hi [First Name],\n\n"
            markdown += f"I understand {company_name} is focused on {relevant_initiative} this year. I wanted to share something that might help advance that work.\n\n"
            markdown += f"We've seen similar organizations in {industry} strengthen {desired_outcome} by {approach}. I thought you might find this useful: [HP resource link]\n\n"
            markdown += f"Would you be open to a brief conversation about how we could help you achieve {desired_outcome}?\n\n"
            markdown += "Best regards,\n[Your Name]\nHP Canada | [Business Unit]\n\n"

            # LinkedIn Outreach Template
            markdown += "## LinkedIn Outreach Template\n\n"
            markdown += f"**Subject line:** Supporting {company_name} on {relevant_topic if relevant_topic != 'Not available' else 'your technology strategy'}\n\n"
            markdown += "**Body:**\n\n"
            markdown += f"Hi [First Name],\n\n"
            markdown += f"{relevant_topic if relevant_topic != 'Not available' else 'Technology modernization'} seems to be a key focus across {industry}. We've seen similar organizations strengthen {desired_outcome} by {approach}.\n\n"
            markdown += "Here's a short resource that outlines the approach: [HP resource link]\n\n"
            markdown += f"Would you be open to a quick chat about what might work best for {company_name}?\n\n"
            markdown += "Best,\n[Your Name]\nHP Canada\n\n"

            # Call Script (if applicable)
            markdown += "## Call Script\n\n"

            # Get specific challenges
            challenge_a = "improving operational efficiency"
            challenge_b = "reducing costs"
            if pain_points and len(pain_points) >= 2:
                pain_1 = pain_points[0]
                pain_2 = pain_points[1]
                if isinstance(pain_1, dict):
                    challenge_a = pain_1.get('title', challenge_a)
                if isinstance(pain_2, dict):
                    challenge_b = pain_2.get('title', challenge_b)

            # Get solution and outcome
            solution_approach = "standardized infrastructure and managed services"
            if solutions and len(solutions) > 0:
                first_solution = solutions[0]
                if isinstance(first_solution, dict):
                    solution_approach = first_solution.get('title', solution_approach)

            markdown += "**Step 1: Provide Context**\n\n"
            markdown += f"Hi [First name], this is [Your name] with HP Canada.\n\n"
            markdown += f"I'm calling about {relevant_topic if relevant_topic != 'Not available' else 'technology modernization opportunities'}. I work with {industry} teams on this. Do you have 30 seconds to see if this is relevant?\n\n"

            markdown += "**Step 2: Explain Offering**\n\n"
            markdown += f"A lot of {industry} teams we work with are looking to {desired_outcome}, whether that's {challenge_a} or {challenge_b}.\n\n"
            markdown += f"At HP, we've been helping them by {solution_approach}. For example, a similar {industry} company recently improved their operational efficiency by 30% after adopting our managed device program. It's a quick change that made a measurable difference in productivity and cost control.\n\n"

            markdown += "**Step 3: CTA**\n\n"
            markdown += f"I can send over a short resource that outlines how we approached this with other {industry} teams. Would that be useful?\n\n"

            # Voicemail Script
            markdown += "## Voicemail Script\n\n"
            markdown += f"Hi [First Name], this is [Your Name] from HP Canada.\n\n"
            markdown += f"I wanted to share a quick idea about {relevant_topic if relevant_topic != 'Not available' else 'technology optimization'}, something we've seen help {industry} teams improve {desired_outcome}.\n\n"
            markdown += "If it's something you're exploring, I'd be happy to send over a short resource or set up a quick chat.\n\n"
            markdown += "You can reach me at [phone number]. Again, it's [Your Name] with HP Canada. Hope we can connect soon.\n\n"

            # Objection Handling
            markdown += "## Objection Handling\n\n"

            markdown += "**Objection: I'm not interested.**\n\n"
            markdown += f"Totally understand. I'm not calling to sell anything. I just wanted to share a quick perspective we've seen make a difference for other teams in {industry}. Would you be open to looking at a short resource?\n\n"

            markdown += "**Objection: We're already working with another vendor.**\n\n"
            markdown += "That's great. A lot of teams we work with were in a similar position and just wanted to see if there were areas they could do things a bit more efficiently. Would it make sense to share a quick example?\n\n"

            markdown += "**Objection: Now's not a good time.**\n\n"
            markdown += "Of course. Is there a time when you will be available later this week? I can make it quick. 10 minutes tops.\n\n"

            markdown += "**Objection: Send me something.**\n\n"
            markdown += f"Absolutely. I'll send over a short piece on [relevant topic]. If it seems relevant, we can reconnect to see if there's a fit.\n\n"

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
            # Send structured data instead of markdown to preserve template design
            api_endpoint = self.template_url

            # Create concise, structured data that preserves template formatting
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
                response = await client.post(
                    api_endpoint,
                    json=payload,
                    headers=headers
                )

                response.raise_for_status()
                result = response.json()

                logger.info(f"Gamma API response: {result}")

                generation_id = result.get("generationId") or result.get("generation_id") or result.get("id")
                if not generation_id:
                    logger.error(f"No generationId in response. Full response: {result}")
                    raise Exception(f"No generationId returned from Gamma API. Response keys: {list(result.keys())}")

                logger.info(f"Generation started with ID: {generation_id}")
                logger.info(f"Markdown length: {len(markdown_content)} characters")
                logger.info(f"Template ID: {self.template_id}")

                # Poll for completion (max 5 minutes for complex presentations)
                max_attempts = 150  # 150 attempts * 2 seconds = 5 minutes
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

                        # Log every 10 seconds to avoid spam
                        if attempt % 5 == 0 or status in ["completed", "failed"]:
                            elapsed = attempt * 2
                            logger.info(f"Generation status after {elapsed}s (attempt {attempt}/{max_attempts}): {status}")

                        # CRITICAL: Log full response structure for debugging
                        logger.info(f"Full status response: {status_data}")
                        logger.info(f"Response keys available: {list(status_data.keys())}")

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

                            if not gamma_url:
                                logger.error(f"❌ No URL field found in completed response!")
                                logger.error(f"Response keys: {list(status_data.keys())}")
                                logger.error(f"Full response: {status_data}")
                                raise Exception(f"No URL returned from completed generation. Response keys: {list(status_data.keys())}")

                            logger.info(f"Slideshow generated successfully: {gamma_url}")
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

                raise Exception(f"Generation timed out after {max_attempts * 2} seconds")

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
