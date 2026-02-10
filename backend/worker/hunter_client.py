"""
Hunter.io API client for email verification and enrichment.
"""
import logging
import httpx
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class HunterClient:
    """
    Client for Hunter.io API to verify and enrich email addresses.

    Features:
    - Email verification (deliverability)
    - Email finder by name and domain
    - Confidence scores
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Hunter.io client.

        Args:
            api_key: Hunter.io API key (from environment)

        Note:
            This value must be provided via environment variables.
        """
        self.api_key = api_key or os.getenv("HUNTER_API_KEY")
        self.api_url = "https://api.hunter.io/v2"
        self.timeout = 10

    async def verify_email(self, email: str) -> Dict[str, Any]:
        """
        Verify an email address.

        Args:
            email: Email address to verify

        Returns:
            Dictionary with verification results
        """
        if not self.api_key:
            logger.warning("Hunter.io API key not configured")
            return {"verified": False, "confidence": 0, "error": "API key not configured"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.api_url}/email-verifier",
                    params={
                        "email": email,
                        "api_key": self.api_key
                    }
                )

                response.raise_for_status()
                data = response.json()

                verification = data.get("data", {})

                return {
                    "verified": verification.get("status") in ["valid", "accept_all"],
                    "confidence": verification.get("score", 0),
                    "status": verification.get("status"),
                    "email": email,
                    "disposable": verification.get("disposable", False),
                    "webmail": verification.get("webmail", False)
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"Hunter.io HTTP error: {e.response.status_code}")
            return {"verified": False, "confidence": 0, "error": str(e)}

        except Exception as e:
            logger.error(f"Hunter.io error: {e}")
            return {"verified": False, "confidence": 0, "error": str(e)}

    async def find_email(
        self,
        domain: str,
        first_name: str,
        last_name: str
    ) -> Dict[str, Any]:
        """
        Find email address for a person at a company.

        Args:
            domain: Company domain
            first_name: Person's first name
            last_name: Person's last name

        Returns:
            Dictionary with found email and confidence
        """
        if not self.api_key:
            logger.warning("Hunter.io API key not configured")
            return {"found": False, "confidence": 0, "error": "API key not configured"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.api_url}/email-finder",
                    params={
                        "domain": domain,
                        "first_name": first_name,
                        "last_name": last_name,
                        "api_key": self.api_key
                    }
                )

                response.raise_for_status()
                data = response.json()

                email_data = data.get("data", {})

                return {
                    "found": bool(email_data.get("email")),
                    "email": email_data.get("email"),
                    "confidence": email_data.get("score", 0),
                    "position": email_data.get("position"),
                    "sources": email_data.get("sources", [])
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"Hunter.io HTTP error: {e.response.status_code}")
            return {"found": False, "confidence": 0, "error": str(e)}

        except Exception as e:
            logger.error(f"Hunter.io error: {e}")
            return {"found": False, "confidence": 0, "error": str(e)}

    async def enrich_stakeholder_emails(
        self,
        stakeholders: list,
        domain: str
    ) -> list:
        """
        Enrich stakeholder profiles with verified emails.

        Args:
            stakeholders: List of stakeholder profiles
            domain: Company domain

        Returns:
            List of enriched stakeholder profiles
        """
        enriched = []

        for stakeholder in stakeholders:
            name = stakeholder.get("name", "")
            existing_email = stakeholder.get("email")

            # If email exists, verify it
            if existing_email and existing_email != "Not available":
                verification = await self.verify_email(existing_email)
                stakeholder["email_verified"] = verification.get("verified", False)
                stakeholder["email_confidence"] = verification.get("confidence", 0)

            # If no email, try to find it
            elif name and domain:
                name_parts = name.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = name_parts[-1]

                    find_result = await self.find_email(domain, first_name, last_name)

                    if find_result.get("found"):
                        stakeholder["email"] = find_result["email"]
                        stakeholder["email_verified"] = True
                        stakeholder["email_confidence"] = find_result["confidence"]
                        logger.info(f"Found email for {name}: {find_result['email']}")

            enriched.append(stakeholder)

        logger.info(f"Enriched {len(enriched)} stakeholder emails with Hunter.io")
        return enriched
