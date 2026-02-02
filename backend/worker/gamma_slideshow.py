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
        company_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a slideshow from company data.

        Args:
            company_data: Finalized company data dictionary

        Returns:
            Dictionary with slideshow URL and status

        Raises:
            Exception: If slideshow creation fails
        """
        try:
            logger.info(
                f"Creating slideshow for {company_data.get('company_name')}"
            )

            # Generate markdown content
            markdown_content = self._generate_markdown(company_data)

            # Send to Gamma API
            result = await self._send_to_gamma(markdown_content)

            logger.info(
                f"Slideshow created successfully: {result.get('url')}"
            )

            return {
                "success": True,
                "slideshow_url": result.get("url"),
                "slideshow_id": result.get("id"),
                "company_name": company_data.get("company_name")
            }

        except Exception as e:
            logger.error(f"Failed to create slideshow: {e}")
            raise

    def _generate_markdown(self, company_data: Dict[str, Any]) -> str:
        """
        Generate markdown content from company data following HP template structure.

        Template slides (based on /template directory screenshots):
        1. Title: Account Intelligence Report with company name
        2. Executive Snapshot: Overview, IT spend, installed tech
        3. Active Buying Signals: Intent topics, trends, news triggers
        4. Opportunity Themes: Priorities, pain points, focus areas
        5. Role Profiles: C-level contacts and strategic priorities
        6. Next Steps: Intent level, recommended actions, assets
        7. Supporting Assets: Email templates for outreach

        Args:
            company_data: Finalized company data

        Returns:
            Formatted markdown string matching HP Account Intelligence Report template
        """
        validated_data = company_data.get("validated_data", {})
        company_name = validated_data.get('company_name', 'Company')

        # Get current date for report
        from datetime import datetime
        current_date = datetime.now().strftime("%B %Y")

        markdown = ""

        # SLIDE 1: Title Slide
        markdown += f"# Account Intelligence Report:\n## {company_name}\n\n"
        markdown += f"**Prepared for:** [Salesperson Name]\n\n"
        markdown += f"**By:** HP RAD Intelligence Desk\n\n"
        markdown += f"**Date:** {current_date}\n\n"
        markdown += "---\n\n"

        # SLIDE 2: Executive Snapshot
        markdown += "# Executive Snapshot\n\n"
        markdown += f"## Account Name\n{company_name}\n\n"

        markdown += "## Company Overview\n"
        overview = validated_data.get('company_overview', validated_data.get('description', 'Industry-leading organization'))
        markdown += f"{overview}\n\n"

        markdown += f"## Account Type\n"
        markdown += f"{validated_data.get('account_type', 'Enterprise')}\n\n"

        markdown += f"## Industry\n"
        markdown += f"{validated_data.get('industry', 'Technology')}\n\n"

        # Estimated IT Spend box
        it_spend = validated_data.get('estimated_it_spend', 'Contact for estimate')
        markdown += f"## Estimated Annual IT Spend\n**${it_spend}**\n\n"

        # Installed technologies
        markdown += "## Installed Technologies\n"
        tech_stack = validated_data.get('technology', validated_data.get('tech_stack', []))
        if isinstance(tech_stack, list) and tech_stack:
            tech_preview = ', '.join(tech_stack[:5])
            markdown += f"{tech_preview}\n\n"
        else:
            markdown += "CRM, Marketing Automation, Sales Tools, Infrastructure\n\n"

        markdown += "---\n\n"

        # SLIDE 3: Active Buying Signals
        markdown += "# Active Buying Signals\n\n"

        markdown += "## Top 3 Intent Topics\n\n"
        intent_topics = validated_data.get('intent_topics', [
            'Cloud Infrastructure',
            'Cybersecurity Solutions',
            'AI & Machine Learning'
        ])
        for i, topic in enumerate(intent_topics[:3], 1):
            markdown += f"### {i:02d}\n{topic}\n\n"

        markdown += "## Top Partner Mentions or Keywords\n"
        partners = validated_data.get('partner_mentions', ['Microsoft', 'AWS', 'Salesforce'])
        markdown += ', '.join(partners[:5]) + "\n\n"

        # Scoops (News & Triggers)
        markdown += "## Scoops (News & Triggers)\n\n"

        markdown += "### Executive Hires\n"
        exec_hires = validated_data.get('executive_hires', 'New CTO recently joined - potential for new vendor preferences')
        markdown += f"{exec_hires}\n\n"

        markdown += "### Funding Announcement\n"
        funding = validated_data.get('funding_news', 'Recent Series B funding - increased spending capacity')
        markdown += f"{funding}\n\n"

        markdown += "### Office Expansions\n"
        expansion = validated_data.get('expansion_news', 'New offices indicate expanded infrastructure needs')
        markdown += f"{expansion}\n\n"

        markdown += "### Partnerships & Acquisitions\n"
        partnerships = validated_data.get('partnership_news', 'Recent acquisitions indicate integration and vendor consolidation needs')
        markdown += f"{partnerships}\n\n"

        markdown += "---\n\n"

        # SLIDE 4: Opportunity Themes
        markdown += "# Opportunity Themes\n\n"

        markdown += "## Emerging Priorities\n\n"
        priorities = validated_data.get('emerging_priorities', [
            'Digital transformation',
            'Cloud migration',
            'Security enhancement'
        ])
        for i, priority in enumerate(priorities[:3], 1):
            markdown += f"### {i:02d}\n{priority}\n\n"

        markdown += "## Pain Point Summary\n"
        pain_points = validated_data.get('pain_points', [
            'Legacy infrastructure limiting agility',
            'Security vulnerabilities requiring modernization',
            'Scalability challenges with current systems'
        ])
        for pain in pain_points[:3]:
            markdown += f"- {pain}\n"
        markdown += "\n"

        markdown += "## Recommended Focus Areas\n"
        focus_areas = validated_data.get('recommended_focus', [
            'Cloud infrastructure modernization',
            'Security and compliance solutions',
            'AI-powered automation tools'
        ])
        for area in focus_areas[:3]:
            markdown += f"- {area}\n"
        markdown += "\n"

        markdown += "---\n\n"

        # SLIDE 5: Role Profiles
        markdown += "# Role Profiles\n\n"

        # Get leadership/contacts data
        leadership = validated_data.get('leadership', {})
        contacts = validated_data.get('contacts', {})

        markdown += "## Role\n"
        markdown += "**CIO / CTO / CISO / COO / CFO / CPO**\n\n"

        markdown += "## Representative Contact\n"
        contact_name = leadership.get('cto', leadership.get('cio', 'Contact Name, Title'))
        markdown += f"{contact_name}\n\n"

        markdown += "## About\n"
        markdown += "Technology leader responsible for digital transformation and IT strategy.\n\n"

        # Contact Details table
        markdown += "## Contact Details\n\n"
        email = contacts.get('email', 'contact@company.com')
        phone = contacts.get('phone', '+1 (555) 000-0000')
        linkedin = contacts.get('linkedin', 'linkedin.com/in/contact')

        markdown += f"| Channel | Details |\n"
        markdown += f"|---------|----------|\n"
        markdown += f"| Email | {email} |\n"
        markdown += f"| Telephone | {phone} |\n"
        markdown += f"| LinkedIn | {linkedin} |\n\n"

        markdown += "## Communication Preference\n"
        markdown += "Email / LinkedIn / Phone / Events\n\n"

        markdown += "## Strategic Priorities\n"
        strategic_priorities = validated_data.get('strategic_priorities', [
            'Infrastructure modernization',
            'Cost optimization',
            'Security enhancement'
        ])
        for priority in strategic_priorities[:3]:
            markdown += f"- {priority}\n"
        markdown += "\n"

        markdown += "## Recommended Talking Points\n"
        markdown += "1-2 sentences of persona-tailored language highlighting how HP solutions address their specific challenges and strategic goals.\n\n"

        markdown += "---\n\n"

        # SLIDE 6: Next Steps and Toolkit
        markdown += "# Next Steps and Toolkit\n\n"

        markdown += "## Intent Level\n"
        intent_level = validated_data.get('intent_level', 'Active Evaluation')
        markdown += f"**{intent_level}**\n\n"
        markdown += "*Early Curiosity / Problem Acknowledgement / Active Evaluation / Decision*\n\n"

        markdown += "## Recommended Next Steps\n\n"
        markdown += "- Introduce emerging trends and thought leadership to build awareness and credibility\n\n"
        markdown += "- Highlight business challenges and frame HP's solutions as ways to address them\n\n"
        markdown += "- Reinforce proof points with case studies and demonstrate integration value\n\n"
        markdown += "- Emphasize ROI, deployment support, and the ease of scaling with HP solutions\n\n"

        markdown += "## Supporting Assets\n\n"
        markdown += "- **Email Template** - Tailored outreach for this account\n\n"
        markdown += "- **LinkedIn Outreach Template** - Social selling messaging\n\n"
        markdown += "- **Call Script** - Key talking points and questions\n\n"

        markdown += "---\n\n"

        # SLIDE 7: Supporting Assets
        markdown += "# Supporting Assets - CIO / CTO / CISO / COO / CFO / CPO\n\n"

        markdown += "## Email Template\n\n"
        markdown += f"**Subject:** Insights for {company_name}'s Digital Transformation\n\n"
        markdown += f"Hi [First Name],\n\n"
        markdown += f"I noticed {company_name}'s recent {validated_data.get('recent_initiative', 'expansion')} "
        markdown += f"and wanted to share some insights on how leading organizations in {validated_data.get('industry', 'your industry')} "
        markdown += "are addressing similar challenges.\n\n"
        markdown += "At HP, we've helped companies like yours with:\n"
        markdown += "- Cloud infrastructure modernization\n"
        markdown += "- Security and compliance solutions\n"
        markdown += "- AI-powered operational efficiency\n\n"
        markdown += "Would you be open to a brief conversation about your current priorities?\n\n"
        markdown += "Best regards,\n"
        markdown += "[Your Name]\n\n"

        markdown += "---\n\n"

        # Data Quality Footer (optional)
        confidence_score = company_data.get("confidence_score", 0)
        markdown += f"\n\n*Data Confidence Score: {confidence_score:.1%} | "
        markdown += f"Sources: {len(validated_data.get('sources', []))}*\n"

        return markdown

    async def _send_to_gamma(self, markdown_content: str) -> Dict[str, Any]:
        """
        Send markdown content to Gamma API for slideshow generation.

        Args:
            markdown_content: Formatted markdown string

        Returns:
            Dictionary with Gamma API response including URL

        Raises:
            Exception: If API request fails
        """
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "inputText": markdown_content,
            "textMode": "preserve",
            "format": "presentation",
            "numCards": 10,
            "textOptions": {
                "tone": "professional",
                "audience": "enterprise sales and business intelligence",
                "language": "en"
            },
            "sharingOptions": {
                "externalAccess": "view"
            }
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:
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

                # Poll for completion (max 120 seconds)
                max_attempts = 60
                attempt = 0

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
                        logger.info(f"Generation status (attempt {attempt}/{max_attempts}): {status}")
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
