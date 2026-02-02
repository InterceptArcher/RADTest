"""
News Intelligence Gatherer using GNews API
Fetches recent company news for sales intelligence.
"""
import logging
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


class NewsGatherer:
    """
    Fetches and categorizes recent company news using GNews API.

    Categories:
    - Executive changes (hires, departures, promotions)
    - Funding announcements (rounds, valuations, investors)
    - Partnerships & acquisitions (strategic deals, M&A)
    - Office expansions (new locations, growth)
    - Product launches (new offerings, major updates)
    - Financial results (earnings, revenue reports)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize news gatherer.

        Args:
            api_key: GNews API key (from environment)

        Note:
            This value must be provided via environment variables.
        """
        self.api_key = api_key or os.getenv("GNEWS_API_KEY")
        self.api_url = "https://gnews.io/api/v4/search"
        self.days_back = 90  # Look back 90 days for relevant news

    async def fetch_company_news(
        self,
        company_name: str,
        domain: Optional[str] = None,
        max_articles: int = 50
    ) -> Dict[str, Any]:
        """
        Fetch recent news articles about a company.

        Args:
            company_name: Company name to search
            domain: Company domain (helps with disambiguation)
            max_articles: Maximum articles to fetch (GNews max is 10 per request)

        Returns:
            Dictionary with categorized news articles
        """
        if not self.api_key:
            logger.warning("GNews API key not configured, returning empty news data")
            return self._empty_response()

        try:
            # Calculate date range (last 90 days)
            from_date = (datetime.now() - timedelta(days=self.days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Build search query
            query = f'"{company_name}"'

            params = {
                "q": query,
                "lang": "en",
                "max": min(max_articles, 10),  # GNews max is 10
                "from": from_date,
                "token": self.api_key,
                "sortby": "publishedAt"
            }

            logger.info(f"Fetching news for {company_name} from GNews (last {self.days_back} days)")

            async with httpx.AsyncClient(timeout=10) as client:  # 10 second timeout
                response = await client.get(self.api_url, params=params)
                response.raise_for_status()
                data = response.json()

                articles = data.get("articles", [])
                logger.info(f"Found {len(articles)} news articles for {company_name}")

                # Categorize articles
                categorized = self._categorize_articles(articles)

                # Extract summaries for each category
                summaries = self._generate_category_summaries(categorized)

                return {
                    "success": True,
                    "company_name": company_name,
                    "articles_count": len(articles),
                    "date_range": f"Last {self.days_back} days",
                    "categories": categorized,
                    "summaries": summaries,
                    "raw_articles": articles
                }

        except httpx.TimeoutException:
            logger.warning(f"GNews API timeout after 10s for {company_name}")
            return self._empty_response(error="GNews API timeout (10s)")

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json().get("errors", [])
            except:
                pass
            logger.error(f"GNews API HTTP error: {e.response.status_code} - {error_detail}")
            return self._empty_response(error=f"GNews API HTTP {e.response.status_code}")

        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return self._empty_response(error=str(e))

    def _categorize_articles(self, articles: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize articles by topic using keyword matching.

        Args:
            articles: List of news articles

        Returns:
            Dictionary of categorized articles
        """
        categories = {
            "executive_changes": [],
            "funding": [],
            "partnerships": [],
            "expansions": [],
            "products": [],
            "financial": [],
            "other": []
        }

        # Keywords for each category
        keywords = {
            "executive_changes": [
                "ceo", "cto", "cfo", "cio", "coo", "hire", "hired", "appoint",
                "joins", "joined", "executive", "resign", "departure", "promoted",
                "chief", "president", "vp", "vice president", "names", "taps"
            ],
            "funding": [
                "funding", "raised", "raises", "investment", "investors", "valuation",
                "series a", "series b", "series c", "series d", "seed", "round",
                "venture", "vc", "capital", "million", "billion", "invested", "financing"
            ],
            "partnerships": [
                "partnership", "partners", "acquisition", "acquires", "acquired",
                "merger", "deal", "agreement", "collaboration", "strategic",
                "alliance", "joint venture", "buys", "purchased", "teams up"
            ],
            "expansions": [
                "expansion", "expands", "new office", "opens", "location",
                "facility", "headquarters", "growth", "scaling", "presence",
                "regional", "international", "global"
            ],
            "products": [
                "launch", "launches", "launched", "product", "service", "feature",
                "release", "unveiled", "announces", "introduced", "new offering",
                "platform", "solution"
            ],
            "financial": [
                "earnings", "revenue", "profit", "quarterly", "financial results",
                "fiscal", "q1", "q2", "q3", "q4", "annual report", "sales",
                "beats estimates", "misses", "guidance"
            ]
        }

        for article in articles:
            title = (article.get("title") or "").lower()
            description = (article.get("description") or "").lower()
            content_text = (article.get("content") or "").lower()
            content = f"{title} {description} {content_text}"

            categorized = False

            # Check each category (prioritize by order)
            for category, terms in keywords.items():
                if any(term in content for term in terms):
                    categories[category].append({
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "content": article.get("content"),
                        "url": article.get("url"),
                        "source": article.get("source", {}).get("name"),
                        "publishedAt": article.get("publishedAt"),
                        "relevance_score": self._calculate_relevance(content, terms)
                    })
                    categorized = True
                    break  # Only categorize once per article

            if not categorized:
                categories["other"].append({
                    "title": article.get("title"),
                    "description": article.get("description"),
                    "content": article.get("content"),
                    "url": article.get("url"),
                    "source": article.get("source", {}).get("name"),
                    "publishedAt": article.get("publishedAt"),
                    "relevance_score": 0.1
                })

        # Sort each category by relevance and date
        for category in categories:
            categories[category] = sorted(
                categories[category],
                key=lambda x: (
                    x.get("relevance_score", 0),
                    x.get("publishedAt", "")
                ),
                reverse=True
            )

        return categories

    def _calculate_relevance(self, content: str, keywords: List[str]) -> float:
        """Calculate relevance score based on keyword matches."""
        matches = sum(1 for keyword in keywords if keyword in content)
        return min(matches / len(keywords) if keywords else 0, 1.0)

    def _generate_category_summaries(self, categories: Dict[str, List[Dict]]) -> Dict[str, str]:
        """
        Generate human-readable summaries for each category.

        Args:
            categories: Categorized articles

        Returns:
            Dictionary of category summaries
        """
        summaries = {}

        # Executive Changes
        if categories["executive_changes"]:
            top_article = categories["executive_changes"][0]
            summaries["executive_hires"] = (
                f"{top_article['title']} ({self._format_date(top_article['publishedAt'])})"
            )
        else:
            summaries["executive_hires"] = "No recent executive changes found"

        # Funding
        if categories["funding"]:
            top_article = categories["funding"][0]
            summaries["funding_news"] = (
                f"{top_article['title']} ({self._format_date(top_article['publishedAt'])})"
            )
        else:
            summaries["funding_news"] = "No recent funding announcements found"

        # Partnerships
        if categories["partnerships"]:
            top_article = categories["partnerships"][0]
            summaries["partnership_news"] = (
                f"{top_article['title']} ({self._format_date(top_article['publishedAt'])})"
            )
        else:
            summaries["partnership_news"] = "No recent partnership or acquisition news found"

        # Expansions
        if categories["expansions"]:
            top_article = categories["expansions"][0]
            summaries["expansion_news"] = (
                f"{top_article['title']} ({self._format_date(top_article['publishedAt'])})"
            )
        else:
            summaries["expansion_news"] = "No recent expansion news found"

        return summaries

    def _format_date(self, date_str: str) -> str:
        """Format ISO date to readable format."""
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%b %d, %Y")
        except:
            return date_str

    def _empty_response(self, error: Optional[str] = None) -> Dict[str, Any]:
        """Return empty response structure."""
        return {
            "success": False,
            "company_name": "",
            "articles_count": 0,
            "date_range": "",
            "categories": {
                "executive_changes": [],
                "funding": [],
                "partnerships": [],
                "expansions": [],
                "products": [],
                "financial": [],
                "other": []
            },
            "summaries": {
                "executive_hires": "No news data available",
                "funding_news": "No news data available",
                "partnership_news": "No news data available",
                "expansion_news": "No news data available"
            },
            "raw_articles": [],
            "error": error
        }


async def gather_company_news(company_name: str, domain: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to gather company news.

    Args:
        company_name: Company name
        domain: Optional company domain

    Returns:
        News data dictionary
    """
    gatherer = NewsGatherer()
    return await gatherer.fetch_company_news(company_name, domain)
