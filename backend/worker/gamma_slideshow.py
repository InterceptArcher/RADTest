"""
Gamma API slideshow creation module.
Creates markdown prompts and generates slideshows via Gamma API.
"""
import logging
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
        self.api_url = "https://api.gamma.app/v1/generate"
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
        Generate markdown content from company data.

        Args:
            company_data: Finalized company data

        Returns:
            Formatted markdown string
        """
        validated_data = company_data.get("validated_data", {})

        markdown = f"# {validated_data.get('company_name', 'Company Profile')}\n\n"

        # Company Overview Section
        markdown += "## Company Overview\n\n"
        markdown += f"**Domain:** {validated_data.get('domain', 'N/A')}\n\n"
        markdown += f"**Industry:** {validated_data.get('industry', 'N/A')}\n\n"
        markdown += f"**Headquarters:** {validated_data.get('headquarters', 'N/A')}\n\n"
        markdown += "---\n\n"

        # Key Metrics Section
        markdown += "## Key Metrics\n\n"
        markdown += f"- **Employee Count:** {validated_data.get('employee_count', 'N/A')}\n"
        markdown += f"- **Revenue:** {validated_data.get('revenue', 'N/A')}\n"
        markdown += f"- **Funding:** {validated_data.get('funding', 'N/A')}\n"
        markdown += f"- **Founded:** {validated_data.get('founded_year', 'N/A')}\n\n"
        markdown += "---\n\n"

        # Leadership Section
        if "leadership" in validated_data:
            markdown += "## Leadership\n\n"
            leadership = validated_data["leadership"]

            if "ceo" in leadership:
                markdown += f"**CEO:** {leadership['ceo']}\n\n"

            if "founders" in leadership:
                markdown += f"**Founders:** {', '.join(leadership['founders'])}\n\n"

            markdown += "---\n\n"

        # Technology Stack Section
        if "technology" in validated_data:
            markdown += "## Technology Stack\n\n"
            tech = validated_data["technology"]

            if isinstance(tech, list):
                for item in tech:
                    markdown += f"- {item}\n"
            else:
                markdown += f"{tech}\n"

            markdown += "\n---\n\n"

        # Market Presence Section
        markdown += "## Market Presence\n\n"
        markdown += f"**Target Market:** {validated_data.get('target_market', 'N/A')}\n\n"
        markdown += f"**Geographic Reach:** {validated_data.get('geographic_reach', 'N/A')}\n\n"
        markdown += "---\n\n"

        # Contact Information Section
        markdown += "## Contact Information\n\n"

        if "contacts" in validated_data:
            contacts = validated_data["contacts"]
            markdown += f"**Website:** {contacts.get('website', 'N/A')}\n\n"
            markdown += f"**LinkedIn:** {contacts.get('linkedin', 'N/A')}\n\n"
            markdown += f"**Email:** {contacts.get('email', 'N/A')}\n\n"

        markdown += "---\n\n"

        # Data Quality Section
        confidence_score = company_data.get("confidence_score", 0)
        markdown += "## Data Quality\n\n"
        markdown += f"**Confidence Score:** {confidence_score:.1%}\n\n"
        markdown += f"**Data Sources:** {len(validated_data.get('sources', []))} sources\n\n"

        # Validation metadata
        validation_meta = company_data.get("validation_metadata", {})
        if "validated_fields" in validation_meta:
            markdown += f"**Validated Fields:** {validation_meta['validated_fields']}\n\n"

        return markdown

    async def _send_to_gamma(self, markdown_content: str) -> Dict[str, Any]:
        """
        Send markdown content to Gamma API for slideshow generation.

        Args:
            markdown_content: Formatted markdown string

        Returns:
            Dictionary with Gamma API response

        Raises:
            Exception: If API request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "content": markdown_content,
            "format": "markdown",
            "theme": "professional",
            "options": {
                "auto_layout": True,
                "slide_numbers": True,
                "title_slide": True
            }
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )

                response.raise_for_status()

                result = response.json()

                return {
                    "url": result.get("url"),
                    "id": result.get("id"),
                    "status": "generated"
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"Gamma API HTTP error: {e.response.status_code}")
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
