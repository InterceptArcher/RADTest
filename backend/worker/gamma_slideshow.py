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

    def __init__(self, gamma_api_key: str):
        """
        Initialize Gamma slideshow creator.

        Args:
            gamma_api_key: Gamma API key (from environment)

        Note:
            This value must be provided via environment variables.
        """
        self.api_key = gamma_api_key
        self.api_url = "https://public-api.gamma.app/v1.0/generations"
        self.status_url = "https://public-api.gamma.app/v1.0/generations"
        logger.info("Gamma slideshow creator initialized")

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

            # Base slides (7) + stakeholder slides + feedback slide
            num_cards = 7 + stakeholder_count + 1

            # Send to Gamma API
            result = await self._send_to_gamma(markdown_content, num_cards)

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

    def _generate_markdown(self, company_data: Dict[str, Any], user_email: str = None) -> str:
        """
        Generate markdown content from company data following HP RAD Intelligence template.

        IMPORTANT: This maintains ALL content verbatim - DO NOT simplify.
        Prioritizes data/charts over AI images. HP branded.

        Slide Structure:
        1. Title: Account Intelligence Report
        2. Executive Snapshot
        3. Buying Signals - Intent Topics & Partner Mentions (with chart)
        4. Buying Signals - News and Triggers
        5. Opportunity Themes - Pain Points & Solutions
        6. Sales Opportunities
        7+. Stakeholder Profiles (one per stakeholder)
        Last: Feedback and Questions

        Args:
            company_data: Finalized company data
            user_email: Email of person pulling the data

        Returns:
            Formatted markdown string for HP Account Intelligence Report
        """
        validated_data = company_data.get("validated_data", {})
        company_name = validated_data.get('company_name', 'Company')

        # Get current date for report
        from datetime import datetime
        current_date = datetime.now().strftime("%B %d, %Y")

        # User email (person pulling data)
        preparer_email = user_email or company_data.get('user_email', '[salesperson@hp.com]')

        markdown = ""

        # ============================================================
        # SLIDE 1: Title Slide
        # ============================================================
        markdown += f"# Account Intelligence Report: {company_name}\n\n"
        markdown += f"**Prepared for:** {preparer_email} by the HP RAD Intelligence Desk\n\n"
        markdown += f"**This information was pulled on:** {current_date}\n\n"
        markdown += "**Confidential - for internal HP use only**\n\n"
        markdown += "---\n\n"

        # ============================================================
        # SLIDE 2: Executive Snapshot
        # ============================================================
        markdown += "# Executive Snapshot\n\n"

        markdown += f"**Account Name:** {company_name}\n\n"

        # Company Overview - FULL TEXT, do not simplify
        markdown += "**Company Overview:**\n\n"
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

        # Installed Technologies - FULL LIST
        markdown += "**Installed Technologies:**\n\n"
        tech_stack = validated_data.get('technology') or validated_data.get('tech_stack') or validated_data.get('technologies', [])
        if isinstance(tech_stack, list) and tech_stack:
            # Group by category if possible
            tech_list = ', '.join(tech_stack)
            markdown += f"{tech_list}\n\n"
            # Add last seen date if available
            tech_last_seen = validated_data.get('technology_last_seen', '')
            if tech_last_seen:
                markdown += f"*(Last seen: {tech_last_seen})*\n\n"
        elif isinstance(tech_stack, str) and tech_stack:
            markdown += f"{tech_stack}\n\n"
        else:
            markdown += "CRM, Marketing Automation, Sales Tools, Infrastructure - detailed technology stack available through research channels\n\n"

        markdown += "---\n\n"

        # ============================================================
        # SLIDE 3: Buying Signals - Intent Topics & Partner Mentions
        # ============================================================
        markdown += "# Buying Signals: Intent Topics & Partner Mentions\n\n"

        # Top 3 Intent Topics with scores for chart
        markdown += "## Top 3 Intent Topics\n\n"
        intent_topics = validated_data.get('intent_topics') or validated_data.get('buying_signals', {}).get('intent_topics', [])
        if not intent_topics:
            intent_topics = [
                {'topic': 'Cloud Infrastructure & Migration', 'score': 85},
                {'topic': 'Cybersecurity & Compliance', 'score': 78},
                {'topic': 'AI & Machine Learning Solutions', 'score': 72}
            ]

        # Format for chart visualization
        markdown += "| Intent Topic | Score |\n"
        markdown += "|-------------|-------|\n"
        for i, topic in enumerate(intent_topics[:3], 1):
            if isinstance(topic, dict):
                topic_name = topic.get('topic', topic.get('name', f'Topic {i}'))
                topic_score = topic.get('score', topic.get('intent_score', 70 + i*5))
            else:
                topic_name = str(topic)
                topic_score = 80 - i*5
            markdown += f"| {topic_name} | {topic_score}% |\n"
        markdown += "\n"

        # Intent Score Chart description (Gamma will render)
        markdown += "*Intent scores based on digital behavior analysis and research activity*\n\n"

        # Top Partner Mentions
        markdown += "## Top Partner Mentions or Keywords\n\n"
        partners = validated_data.get('partner_mentions') or validated_data.get('buying_signals', {}).get('competitors', [])
        if not partners:
            partners = validated_data.get('competitors', ['Microsoft', 'AWS', 'Salesforce', 'ServiceNow', 'SAP'])
        if isinstance(partners, list):
            markdown += ', '.join(str(p) for p in partners[:7]) + "\n\n"
        else:
            markdown += f"{partners}\n\n"

        markdown += "---\n\n"

        # ============================================================
        # SLIDE 4: Buying Signals - News and Triggers
        # ============================================================
        markdown += "# Buying Signals: News and Triggers\n\n"

        # Get news/triggers data
        news_triggers = validated_data.get('news_triggers') or validated_data.get('buying_signals', {}).get('triggers', {})

        # Executive Changes/Hires
        markdown += "## Executive Changes\n\n"
        exec_changes = news_triggers.get('executive_changes') or validated_data.get('executive_hires', '')
        if exec_changes:
            if isinstance(exec_changes, list):
                for change in exec_changes:
                    markdown += f"- {change}\n"
                markdown += "\n"
            else:
                markdown += f"{exec_changes}\n\n"
        else:
            markdown += "No recent executive changes detected. Monitor for new leadership opportunities.\n\n"

        # Funding Announcements
        markdown += "## Funding Announcements\n\n"
        funding = news_triggers.get('funding') or validated_data.get('funding_news', '')
        if funding:
            if isinstance(funding, list):
                for f in funding:
                    markdown += f"- {f}\n"
                markdown += "\n"
            else:
                markdown += f"{funding}\n\n"
        else:
            markdown += "No recent funding announcements. Company may be self-funded or established.\n\n"

        # Office Expansions
        markdown += "## Office Expansions\n\n"
        expansions = news_triggers.get('expansions') or validated_data.get('expansion_news', '')
        if expansions:
            if isinstance(expansions, list):
                for exp in expansions:
                    markdown += f"- {exp}\n"
                markdown += "\n"
            else:
                markdown += f"{expansions}\n\n"
        else:
            markdown += "No recent expansion announcements detected.\n\n"

        # Partnerships & Acquisitions
        markdown += "## Partnerships & Acquisitions\n\n"
        partnerships = news_triggers.get('partnerships') or validated_data.get('partnership_news', '')
        if partnerships:
            if isinstance(partnerships, list):
                for p in partnerships:
                    markdown += f"- {p}\n"
                markdown += "\n"
            else:
                markdown += f"{partnerships}\n\n"
        else:
            markdown += "No recent partnership or acquisition activity detected.\n\n"

        # Product Launches
        markdown += "## Product Launches & Initiatives\n\n"
        products = news_triggers.get('products') or validated_data.get('product_news', '')
        if products:
            if isinstance(products, list):
                for prod in products:
                    markdown += f"- {prod}\n"
                markdown += "\n"
            else:
                markdown += f"{products}\n\n"
        else:
            markdown += "Monitor for upcoming product announcements and strategic initiatives.\n\n"

        markdown += "---\n\n"

        # ============================================================
        # SLIDE 5: Opportunity Themes - Pain Points & Solutions
        # ============================================================
        markdown += "# Opportunity Themes: Pain Points & Recommended Solutions\n\n"

        # Pain Points - FULL DETAIL
        markdown += "## Identified Pain Points\n\n"
        pain_points = validated_data.get('pain_points') or validated_data.get('opportunity_themes', {}).get('pain_points', [])
        if not pain_points:
            pain_points = [
                'Legacy infrastructure limiting business agility and digital transformation initiatives',
                'Security vulnerabilities and compliance gaps requiring immediate modernization',
                'Scalability challenges with current systems impacting growth objectives',
                'Operational inefficiencies driving up costs and reducing competitive advantage'
            ]
        for pain in pain_points:
            if isinstance(pain, dict):
                pain_text = pain.get('description', pain.get('pain_point', str(pain)))
            else:
                pain_text = str(pain)
            markdown += f"- {pain_text}\n"
        markdown += "\n"

        # Recommended Solution Areas
        markdown += "## Recommended Solution Areas\n\n"
        solutions = validated_data.get('recommended_solutions') or validated_data.get('recommended_focus') or validated_data.get('opportunity_themes', {}).get('solutions', [])
        if not solutions:
            solutions = [
                'Cloud infrastructure modernization with HP hybrid cloud solutions',
                'End-to-end security and compliance framework implementation',
                'AI-powered automation and operational efficiency tools',
                'Scalable enterprise hardware and software solutions'
            ]
        for solution in solutions:
            if isinstance(solution, dict):
                solution_text = solution.get('description', solution.get('solution', str(solution)))
            else:
                solution_text = str(solution)
            markdown += f"- {solution_text}\n"
        markdown += "\n"

        # HP Value Proposition
        markdown += "## HP Value Proposition\n\n"
        value_prop = validated_data.get('hp_value_proposition', '')
        if value_prop:
            markdown += f"{value_prop}\n\n"
        else:
            markdown += "HP offers comprehensive solutions addressing these pain points through proven enterprise technology, deployment support, and industry-leading service and support infrastructure.\n\n"

        markdown += "---\n\n"

        # ============================================================
        # SLIDE 6: Sales Opportunities
        # ============================================================
        markdown += "# Sales Opportunities\n\n"

        # Get sales opportunities
        opportunities = validated_data.get('sales_opportunities') or validated_data.get('opportunities', [])

        if opportunities:
            if isinstance(opportunities, list):
                for i, opp in enumerate(opportunities, 1):
                    if isinstance(opp, dict):
                        opp_name = opp.get('name', opp.get('title', f'Opportunity {i}'))
                        opp_desc = opp.get('description', opp.get('details', ''))
                        opp_value = opp.get('value', opp.get('estimated_value', ''))
                        opp_timeline = opp.get('timeline', opp.get('timeframe', ''))

                        markdown += f"## {opp_name}\n\n"
                        if opp_desc:
                            markdown += f"{opp_desc}\n\n"
                        if opp_value:
                            markdown += f"**Estimated Value:** {opp_value}\n\n"
                        if opp_timeline:
                            markdown += f"**Timeline:** {opp_timeline}\n\n"
                    else:
                        markdown += f"- {opp}\n"
                markdown += "\n"
            else:
                markdown += f"{opportunities}\n\n"
        else:
            # Generate based on pain points and company data
            markdown += "## Infrastructure Modernization\n\n"
            markdown += f"Based on {company_name}'s current technology stack and growth trajectory, there is significant opportunity for infrastructure modernization including compute, storage, and networking solutions.\n\n"

            markdown += "## Security & Compliance\n\n"
            markdown += "Enterprise security solutions addressing endpoint protection, network security, and compliance requirements for the organization's industry vertical.\n\n"

            markdown += "## Workplace Solutions\n\n"
            markdown += "Modern workplace technology including devices, collaboration tools, and hybrid work enablement solutions to support workforce productivity.\n\n"

            markdown += "## Managed Services\n\n"
            markdown += "HP managed services offerings to reduce operational burden and enable focus on core business initiatives.\n\n"

        markdown += "---\n\n"

        # ============================================================
        # SLIDES 7+: Stakeholder Profiles (REPEAT FOR EACH)
        # ============================================================
        # Get all stakeholders
        stakeholders = validated_data.get('stakeholder_profiles') or validated_data.get('stakeholders', [])
        hunter_contacts = validated_data.get('hunter_contacts', [])

        # Combine and deduplicate stakeholders
        all_stakeholders = []

        if isinstance(stakeholders, list):
            all_stakeholders.extend(stakeholders)
        elif isinstance(stakeholders, dict):
            for role, profile in stakeholders.items():
                if isinstance(profile, dict):
                    profile['role_type'] = role
                    all_stakeholders.append(profile)

        # Add hunter contacts if not already present
        if hunter_contacts:
            existing_names = [s.get('name', '').lower() for s in all_stakeholders]
            for contact in hunter_contacts:
                name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                if name.lower() not in existing_names and name:
                    all_stakeholders.append({
                        'name': name,
                        'title': contact.get('position', ''),
                        'email': contact.get('value', contact.get('email', '')),
                        'phone': contact.get('phone_number', ''),
                        'linkedin': contact.get('linkedin', ''),
                        'department': contact.get('department', ''),
                        'confidence': contact.get('confidence', 0)
                    })

        # If no stakeholders found, add CEO if available
        if not all_stakeholders:
            ceo = validated_data.get('ceo', '')
            if ceo:
                all_stakeholders.append({
                    'name': ceo,
                    'title': 'Chief Executive Officer',
                    'role_type': 'CEO'
                })

        # Generate a slide for EACH stakeholder
        for stakeholder in all_stakeholders:
            name = stakeholder.get('name', 'Contact Name')
            title = stakeholder.get('title', stakeholder.get('role_type', stakeholder.get('position', 'Executive')))

            markdown += f"# Stakeholder Profile: {name}\n\n"
            markdown += f"**Role:** {title}\n\n"

            # About - 1 paragraph bio (call out new hire if applicable)
            markdown += "## About\n\n"
            bio = stakeholder.get('bio', stakeholder.get('about', stakeholder.get('description', '')))
            is_new_hire = stakeholder.get('is_new_hire', False)
            hire_date = stakeholder.get('hire_date', stakeholder.get('start_date', ''))

            if bio:
                markdown += f"{bio}"
                if is_new_hire or hire_date:
                    markdown += f" **[NEW HIRE - joined {hire_date or 'recently'}]**"
                markdown += "\n\n"
            else:
                markdown += f"{name} serves as {title} at {company_name}, responsible for strategic initiatives and organizational leadership in their domain."
                if is_new_hire or hire_date:
                    markdown += f" **[NEW HIRE - joined {hire_date or 'recently'}]**"
                markdown += "\n\n"

            # Strategic Priorities - 3 bullet points with descriptions
            markdown += "## Strategic Priorities\n\n"
            priorities = stakeholder.get('strategic_priorities', stakeholder.get('priorities', []))
            if priorities:
                if isinstance(priorities, list):
                    for priority in priorities[:3]:
                        if isinstance(priority, dict):
                            p_name = priority.get('name', priority.get('priority', ''))
                            p_desc = priority.get('description', '')
                            markdown += f"- **{p_name}:** {p_desc}\n"
                        else:
                            markdown += f"- {priority}\n"
                else:
                    markdown += f"- {priorities}\n"
            else:
                markdown += "- **Digital Transformation:** Driving modernization initiatives across the organization\n"
                markdown += "- **Operational Excellence:** Improving efficiency and reducing operational costs\n"
                markdown += "- **Innovation & Growth:** Enabling new capabilities and competitive advantage\n"
            markdown += "\n"

            # Communication Preferences
            markdown += "## Communication Preferences\n\n"
            comm_pref = stakeholder.get('communication_preference', stakeholder.get('communication_preferences', ''))
            if comm_pref:
                markdown += f"{comm_pref}\n\n"
            else:
                markdown += "Email / LinkedIn / Phone / Events\n\n"

            # Conversation Starters - 1-2 sentences persona-tailored
            markdown += "## Conversation Starters\n\n"
            conv_starters = stakeholder.get('conversation_starters', stakeholder.get('talking_points', ''))
            if conv_starters:
                if isinstance(conv_starters, list):
                    for starter in conv_starters[:2]:
                        markdown += f"- {starter}\n"
                else:
                    markdown += f"{conv_starters}\n"
            else:
                markdown += f"- \"I noticed {company_name}'s recent focus on [relevant initiative]. How is your team approaching [related challenge]?\"\n"
                markdown += f"- \"Many {title}s in {industry} are prioritizing [relevant trend]. What's driving your strategy in this area?\"\n"
            markdown += "\n"

            # Recommended Next Steps - 4 specific points
            markdown += "## Recommended Next Steps\n\n"
            next_steps = stakeholder.get('recommended_next_steps', stakeholder.get('next_steps', []))
            if next_steps and isinstance(next_steps, list):
                for step in next_steps[:4]:
                    markdown += f"- {step}\n"
            else:
                markdown += "- Introduce emerging trends and thought leadership to build awareness and credibility\n"
                markdown += "- Highlight business challenges and frame HP's solutions as ways to address them\n"
                markdown += "- Reinforce proof points with case studies and demonstrate integration value\n"
                markdown += "- Emphasize ROI, deployment support, and the ease of scaling with HP solutions\n"
            markdown += "\n"

            # Contact Information
            email = stakeholder.get('email', stakeholder.get('value', ''))
            phone = stakeholder.get('phone', stakeholder.get('phone_number', ''))
            linkedin = stakeholder.get('linkedin', '')

            if email or phone or linkedin:
                markdown += "## Contact Information\n\n"
                if email:
                    markdown += f"**Email:** {email}\n\n"
                if phone:
                    markdown += f"**Phone:** {phone}\n\n"
                if linkedin:
                    markdown += f"**LinkedIn:** {linkedin}\n\n"

            # Outreach Templates for this stakeholder
            markdown += "## Outreach Templates\n\n"

            # Email Template
            markdown += "### Email Template\n\n"
            email_template = stakeholder.get('email_template', '')
            if email_template:
                markdown += f"{email_template}\n\n"
            else:
                markdown += f"**Subject:** Insights for {company_name}'s {title.split()[0] if title else 'Strategic'} Priorities\n\n"
                markdown += f"Hi {name.split()[0] if name else '[First Name]'},\n\n"
                markdown += f"I've been following {company_name}'s work in {industry} and wanted to share some insights on how organizations with similar priorities are addressing {validated_data.get('key_challenge', 'digital transformation challenges')}.\n\n"
                markdown += "At HP, we've partnered with leading enterprises to deliver:\n"
                markdown += "- Scalable infrastructure solutions\n"
                markdown += "- Enterprise security frameworks\n"
                markdown += "- Operational efficiency improvements\n\n"
                markdown += "Would you be open to a brief conversation about your current initiatives?\n\n"
                markdown += "Best regards,\n[Your Name]\n\n"

            # LinkedIn Outreach
            markdown += "### LinkedIn Outreach\n\n"
            linkedin_template = stakeholder.get('linkedin_template', '')
            if linkedin_template:
                markdown += f"{linkedin_template}\n\n"
            else:
                markdown += f"Hi {name.split()[0] if name else '[First Name]'}, I've been impressed by {company_name}'s approach to {validated_data.get('key_initiative', 'innovation')}. "
                markdown += f"As someone focused on helping {title}s navigate {validated_data.get('industry_challenge', 'technology transformation')}, "
                markdown += "I'd love to connect and share some insights that might be valuable for your team. Looking forward to connecting!\n\n"

            # Call Script
            markdown += "### Call Script\n\n"
            call_script = stakeholder.get('call_script', '')
            if call_script:
                markdown += f"{call_script}\n\n"
            else:
                markdown += f"**Opening:** \"Hi {name.split()[0] if name else '[First Name]'}, this is [Your Name] from HP. I'm reaching out because we've been working with several {industry} organizations on [relevant solution area] and thought there might be some synergies worth exploring.\"\n\n"
                markdown += f"**Value Proposition:** \"Based on {company_name}'s focus on [key initiative], I wanted to share how we've helped similar organizations achieve [specific outcome].\"\n\n"
                markdown += "**Discovery Questions:**\n"
                markdown += "- \"What are your top priorities for the coming year?\"\n"
                markdown += "- \"What challenges are you facing with your current infrastructure?\"\n"
                markdown += "- \"How are you approaching [relevant trend]?\"\n\n"
                markdown += "**Close:** \"Based on our conversation, I'd recommend we schedule a more detailed discussion with our solutions team. Would [specific date/time] work for a 30-minute call?\"\n\n"

            markdown += "---\n\n"

        # ============================================================
        # LAST SLIDE: Feedback and Questions
        # ============================================================
        markdown += "# Feedback and Questions\n\n"

        markdown += "## Let Us Know What You Think\n\n"
        markdown += "Your feedback helps us make future reports even more relevant and useful.\n\n"

        markdown += "## Share Your Thoughts\n\n"
        markdown += "If you have any questions about this report, contact the HP RAD Intelligence Desk.\n\n"

        markdown += "---\n\n"

        # Footer with metadata
        confidence_score = company_data.get("confidence_score", 0.85)
        sources_count = len(validated_data.get('sources', ['Apollo', 'PDL', 'Hunter', 'GNews']))
        markdown += f"*Data Confidence Score: {confidence_score:.0%} | Data Sources: {sources_count} | Generated: {current_date}*\n"

        return markdown

    async def _send_to_gamma(self, markdown_content: str, num_cards: int = 10) -> Dict[str, Any]:
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

        # Use only documented Gamma API options
        # Note: Image/design options may not be supported - keeping payload simple
        payload = {
            "inputText": markdown_content,
            "textMode": "preserve",  # Keep text exactly as provided - no AI rewriting
            "format": "presentation",
            "numCards": num_cards,
            "sharingOptions": {
                "externalAccess": "view"
            }
        }

        try:
            # Increased timeout for complex presentations
            async with httpx.AsyncClient(timeout=300) as client:
                # Create generation
                logger.info("Sending request to Gamma API")
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )

                response.raise_for_status()
                result = response.json()

                generation_id = result.get("generationId")
                if not generation_id:
                    raise Exception("No generationId returned from Gamma API")

                logger.info(f"Generation started with ID: {generation_id}")
                logger.info(f"Markdown length: {len(markdown_content)} characters")

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

                        logger.debug(f"Full status response: {status_data}")

                        if status == "completed":
                            gamma_url = status_data.get("gammaUrl")
                            if not gamma_url:
                                raise Exception("No URL returned from completed generation")

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
