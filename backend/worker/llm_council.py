"""
LLM Council and Revolver resolution logic.
Implements multi-agent decision making for data conflict resolution.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import openai

logger = logging.getLogger(__name__)


class SourceTier(Enum):
    """Reliability tiers for data sources."""
    TIER_1 = 1.0  # Highest reliability
    TIER_2 = 0.8
    TIER_3 = 0.6
    TIER_4 = 0.4
    TIER_5 = 0.2  # Lowest reliability


@dataclass
class CouncilSignal:
    """Signal from a council member LLM agent."""
    agent_id: int
    preferred_value: Any
    confidence: float
    reasoning: str
    reliability_weight: float
    recency_score: float
    agreement_score: float


@dataclass
class ResolutionDecision:
    """Final decision from the revolver agent."""
    winner_value: Any
    confidence_score: float
    alternatives: List[tuple[Any, float]]  # (value, score) pairs
    rules_applied: List[str]
    council_signals: List[CouncilSignal]
    audit_log: List[str]


class LLMCouncil:
    """
    Council of LLM agents for data conflict resolution.

    Architecture:
    - 10-20 LLM agents evaluate data independently
    - Each provides signals, not final decisions
    - Revolver agent consolidates signals and applies rules
    """

    def __init__(
        self,
        openai_api_key: str,
        council_size: int = 10,
        model: str = "gpt-4"
    ):
        """
        Initialize LLM council.

        Args:
            openai_api_key: OpenAI API key (from environment)
            council_size: Number of LLM agents in council (10-20)
            model: OpenAI model to use

        Note:
            API key must be provided via environment variables.
        """
        openai.api_key = openai_api_key
        self.council_size = min(max(council_size, 10), 20)
        self.model = model
        logger.info(f"LLM council initialized with {self.council_size} agents")

    async def resolve_conflict(
        self,
        field_name: str,
        field_type: str,
        candidate_values: List[Dict[str, Any]],
        source_reliability: Dict[str, SourceTier]
    ) -> ResolutionDecision:
        """
        Resolve data conflict using council and revolver.

        Args:
            field_name: Name of the field being resolved
            field_type: Type of field (numeric, text, identity)
            candidate_values: List of candidate value dictionaries
                [{
                    "value": ...,
                    "source": ...,
                    "timestamp": ...,
                    "metadata": {}
                }, ...]
            source_reliability: Mapping of source names to reliability tiers

        Returns:
            ResolutionDecision with winner and alternatives
        """
        logger.info(
            f"Resolving conflict for '{field_name}' with {self.council_size} agents"
        )

        # Phase 1: Gather signals from council
        signals = await self._gather_council_signals(
            field_name,
            field_type,
            candidate_values,
            source_reliability
        )

        # Phase 2: Revolver consolidates and decides
        decision = self._revolver_decide(
            field_name,
            field_type,
            candidate_values,
            signals,
            source_reliability
        )

        logger.info(
            f"Resolution complete for '{field_name}': "
            f"Winner={decision.winner_value}, "
            f"Confidence={decision.confidence_score:.2f}"
        )

        return decision

    async def _gather_council_signals(
        self,
        field_name: str,
        field_type: str,
        candidate_values: List[Dict[str, Any]],
        source_reliability: Dict[str, SourceTier]
    ) -> List[CouncilSignal]:
        """
        Gather evaluation signals from all council members.

        Args:
            field_name: Name of the field
            field_type: Type of field
            candidate_values: Candidate values
            source_reliability: Source reliability mapping

        Returns:
            List of CouncilSignal objects
        """
        logger.info("Gathering signals from council members")

        # Create tasks for parallel evaluation
        tasks = []
        for agent_id in range(self.council_size):
            tasks.append(
                self._get_agent_signal(
                    agent_id,
                    field_name,
                    field_type,
                    candidate_values,
                    source_reliability
                )
            )

        # Execute all council members in parallel
        signals = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failed signals
        valid_signals = [
            s for s in signals
            if not isinstance(s, Exception) and s is not None
        ]

        logger.info(f"Collected {len(valid_signals)} valid signals from council")

        return valid_signals

    async def _get_agent_signal(
        self,
        agent_id: int,
        field_name: str,
        field_type: str,
        candidate_values: List[Dict[str, Any]],
        source_reliability: Dict[str, SourceTier]
    ) -> Optional[CouncilSignal]:
        """
        Get evaluation signal from a single council member.

        Args:
            agent_id: ID of the agent
            field_name: Name of the field
            field_type: Type of field
            candidate_values: Candidate values
            source_reliability: Source reliability mapping

        Returns:
            CouncilSignal or None if evaluation fails
        """
        try:
            prompt = self._create_agent_prompt(
                field_name,
                field_type,
                candidate_values,
                source_reliability
            )

            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are Council Member #{agent_id} in a data "
                            "validation council. Evaluate the candidate values "
                            "and provide your assessment. Focus on evidence, "
                            "not final decisions."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0,
                max_tokens=300
            )

            # Parse response into signal
            signal = self._parse_agent_response(
                agent_id,
                response.choices[0].message.content,
                candidate_values,
                source_reliability
            )

            return signal

        except Exception as e:
            logger.warning(f"Agent {agent_id} failed to provide signal: {e}")
            return None

    def _create_agent_prompt(
        self,
        field_name: str,
        field_type: str,
        candidate_values: List[Dict[str, Any]],
        source_reliability: Dict[str, SourceTier]
    ) -> str:
        """Create prompt for council member evaluation."""
        prompt = f"Field: {field_name} (Type: {field_type})\n\n"
        prompt += "Candidate values:\n\n"

        for i, val in enumerate(candidate_values, 1):
            source = val.get("source", "unknown")
            tier = source_reliability.get(source, SourceTier.TIER_5)

            prompt += f"{i}. Value: {val['value']}\n"
            prompt += f"   Source: {source} (Tier {tier.name})\n"
            prompt += f"   Timestamp: {val.get('timestamp', 'N/A')}\n"
            prompt += f"   Metadata: {val.get('metadata', {})}\n\n"

        prompt += (
            "Provide your assessment:\n"
            "PREFERRED: <value number>\n"
            "CONFIDENCE: <0-1>\n"
            "REASONING: <brief explanation>\n"
            "RELIABILITY_WEIGHT: <0-1>\n"
            "RECENCY_SCORE: <0-1>\n"
            "AGREEMENT_SCORE: <0-1>"
        )

        return prompt

    def _parse_agent_response(
        self,
        agent_id: int,
        response_text: str,
        candidate_values: List[Dict[str, Any]],
        source_reliability: Dict[str, SourceTier]
    ) -> CouncilSignal:
        """Parse agent response into CouncilSignal."""
        lines = response_text.strip().split("\n")

        preferred_idx = 0
        confidence = 0.5
        reasoning = ""
        reliability_weight = 0.5
        recency_score = 0.5
        agreement_score = 0.5

        for line in lines:
            if line.startswith("PREFERRED:"):
                try:
                    preferred_idx = int(
                        line.replace("PREFERRED:", "").strip()
                    ) - 1
                except (ValueError, IndexError):
                    preferred_idx = 0

            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(
                        line.replace("CONFIDENCE:", "").strip()
                    )
                except ValueError:
                    confidence = 0.5

            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()

            elif line.startswith("RELIABILITY_WEIGHT:"):
                try:
                    reliability_weight = float(
                        line.replace("RELIABILITY_WEIGHT:", "").strip()
                    )
                except ValueError:
                    reliability_weight = 0.5

            elif line.startswith("RECENCY_SCORE:"):
                try:
                    recency_score = float(
                        line.replace("RECENCY_SCORE:", "").strip()
                    )
                except ValueError:
                    recency_score = 0.5

            elif line.startswith("AGREEMENT_SCORE:"):
                try:
                    agreement_score = float(
                        line.replace("AGREEMENT_SCORE:", "").strip()
                    )
                except ValueError:
                    agreement_score = 0.5

        preferred_value = candidate_values[preferred_idx]["value"]

        return CouncilSignal(
            agent_id=agent_id,
            preferred_value=preferred_value,
            confidence=confidence,
            reasoning=reasoning,
            reliability_weight=reliability_weight,
            recency_score=recency_score,
            agreement_score=agreement_score
        )

    def _revolver_decide(
        self,
        field_name: str,
        field_type: str,
        candidate_values: List[Dict[str, Any]],
        signals: List[CouncilSignal],
        source_reliability: Dict[str, SourceTier]
    ) -> ResolutionDecision:
        """
        Revolver agent makes final decision based on council signals.

        Resolution Rules:
        1. Source Reliability: Higher tier sources have greater weight
        2. Cross-source Agreement: Values from multiple sources preferred
        3. Field Type specific rules
        4. Recency: More recent values preferred

        Args:
            field_name: Name of the field
            field_type: Type of field
            candidate_values: Candidate values
            signals: Council signals
            source_reliability: Source reliability mapping

        Returns:
            ResolutionDecision
        """
        logger.info("Revolver agent consolidating signals")

        audit_log = []
        rules_applied = []

        # Calculate scores for each candidate value
        value_scores = {}

        for val_dict in candidate_values:
            value = val_dict["value"]
            source = val_dict.get("source", "unknown")

            # Base score from source reliability
            tier = source_reliability.get(source, SourceTier.TIER_5)
            base_score = tier.value
            rules_applied.append(f"source_reliability_{tier.name}")

            # Cross-source agreement
            signal_count = sum(
                1 for s in signals if s.preferred_value == value
            )
            agreement_bonus = (signal_count / len(signals)) * 0.3
            rules_applied.append("cross_source_agreement")

            # Council confidence aggregate
            avg_confidence = sum(
                s.confidence for s in signals if s.preferred_value == value
            ) / max(signal_count, 1)

            # Field type specific adjustments
            if field_type == "numeric":
                # Allow small numeric differences
                rules_applied.append("numeric_tolerance")

            elif field_type == "identity":
                # Require stronger evidence for identity fields
                base_score *= 0.9 if signal_count < len(signals) * 0.5 else 1.1
                rules_applied.append("identity_strict")

            # Final score
            final_score = (
                base_score * 0.4 +
                agreement_bonus * 0.3 +
                avg_confidence * 0.3
            )

            value_scores[value] = final_score

            audit_log.append(
                f"Value '{value}': base={base_score:.2f}, "
                f"agreement={agreement_bonus:.2f}, "
                f"confidence={avg_confidence:.2f}, "
                f"final={final_score:.2f}"
            )

        # Sort by score
        sorted_values = sorted(
            value_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        winner_value = sorted_values[0][0]
        confidence_score = sorted_values[0][1]
        alternatives = sorted_values[1:6]  # Top 5 alternatives

        audit_log.append(
            f"Winner: {winner_value} (confidence: {confidence_score:.2f})"
        )

        return ResolutionDecision(
            winner_value=winner_value,
            confidence_score=confidence_score,
            alternatives=alternatives,
            rules_applied=list(set(rules_applied)),
            council_signals=signals,
            audit_log=audit_log
        )

    async def generate_pain_points(
        self,
        company_data: Dict[str, Any],
        news_data: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Generate pain points based on company data and news.

        Args:
            company_data: Company information
            news_data: Recent news articles and summaries

        Returns:
            List of pain point dictionaries with title and description
        """
        try:
            prompt = f"""Based on the following company information and recent news, identify 3 specific business pain points or challenges this company likely faces.

Company: {company_data.get('company_name', 'Unknown')}
Industry: {company_data.get('industry', 'Unknown')}
Employee Count: {company_data.get('employee_count', 'Unknown')}
Recent News: {news_data.get('summaries', {}).get('all', 'No recent news')}

For each pain point, provide:
1. A concise title (5-10 words)
2. A detailed description (2-3 sentences) explaining the challenge

Format as JSON array:
[
  {{"title": "...", "description": "..."}},
  {{"title": "...", "description": "..."}}
]"""

            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert B2B sales analyst specializing in enterprise technology needs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=800
            )

            import json
            content = response.choices[0].message.content
            pain_points = json.loads(content)

            logger.info(f"Generated {len(pain_points)} pain points")
            return pain_points[:3]

        except Exception as e:
            logger.error(f"Failed to generate pain points: {e}")
            return []

    async def generate_opportunities(
        self,
        company_data: Dict[str, Any],
        pain_points: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Generate sales opportunities based on pain points.

        Args:
            company_data: Company information
            pain_points: List of identified pain points

        Returns:
            List of opportunity dictionaries with title and description
        """
        try:
            pain_summary = "\n".join([f"- {p['title']}" for p in pain_points])

            prompt = f"""Based on these pain points for {company_data.get('company_name', 'the company')}, identify 3 specific sales opportunities for HP technology solutions.

Industry: {company_data.get('industry', 'Unknown')}
Pain Points:
{pain_summary}

For each opportunity, provide:
1. A specific title (sales opportunity)
2. A description with qualification questions

Format as JSON array:
[
  {{"title": "...", "description": "..."}}
]"""

            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an HP enterprise sales strategist."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=800
            )

            import json
            content = response.choices[0].message.content
            opportunities = json.loads(content)

            logger.info(f"Generated {len(opportunities)} opportunities")
            return opportunities[:3]

        except Exception as e:
            logger.error(f"Failed to generate opportunities: {e}")
            return []

    async def generate_intent_topics(
        self,
        company_data: Dict[str, Any],
        news_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate intent topics with scores based on company activities.

        Args:
            company_data: Company information
            news_data: Recent news and signals

        Returns:
            List of intent topics with scores (0-100)
        """
        try:
            prompt = f"""Based on company activities and news, identify top 3 technology intent topics with scores (0-100).

Company: {company_data.get('company_name')}
Industry: {company_data.get('industry')}
Recent Activities: {news_data.get('summaries', {}).get('all', 'No recent news')}

Provide intent topics with realistic scores based on evidence.

Format as JSON array:
[
  {{"topic": "...", "score": 85, "description": "..."}}
]"""

            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a sales intelligence analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=600
            )

            import json
            content = response.choices[0].message.content
            topics = json.loads(content)

            logger.info(f"Generated {len(topics)} intent topics")
            return topics[:3]

        except Exception as e:
            logger.error(f"Failed to generate intent topics: {e}")
            return []

    async def determine_strategic_roles(
        self,
        company_data: Dict[str, Any],
        pain_points: List[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Determine the top 3 most strategic decision-maker roles for HP to target.

        Analyzes company size, industry, tech stack, pain points, and buying signals
        to identify which C-suite/VP roles are most critical for HP sales success.

        Args:
            company_data: Company information (industry, size, tech, etc.)
            pain_points: Identified pain points/challenges

        Returns:
            List of 3 role titles (e.g., ["CIO", "CFO", "CISO"])
        """
        try:
            # Extract relevant context
            company_name = company_data.get('company_name', 'Company')
            industry = company_data.get('industry', 'Technology')
            employee_count = company_data.get('employee_count', 'Unknown')
            revenue = company_data.get('revenue', company_data.get('annual_revenue', 'Unknown'))
            tech_stack = company_data.get('technologies', company_data.get('technology', []))
            intent_topics = company_data.get('intent_topics', company_data.get('intent_signals', []))

            # Format tech stack
            if isinstance(tech_stack, list):
                tech_str = ', '.join(tech_stack[:10])
            else:
                tech_str = str(tech_stack)

            # Format intent topics
            intent_str = ""
            if intent_topics:
                intent_list = []
                for topic in intent_topics[:5]:
                    if isinstance(topic, dict):
                        intent_list.append(topic.get('topic', topic.get('topic_name', str(topic))))
                    else:
                        intent_list.append(str(topic))
                intent_str = ', '.join(intent_list)

            # Format pain points
            pain_str = ""
            if pain_points:
                pain_list = []
                for pain in pain_points[:3]:
                    if isinstance(pain, dict):
                        pain_list.append(pain.get('title', pain.get('name', str(pain))))
                    else:
                        pain_list.append(str(pain))
                pain_str = '\n'.join([f"- {p}" for p in pain_list])

            prompt = f"""You are an HP enterprise sales strategist. Analyze this company and determine the TOP 3 decision-maker roles that HP should target for IT infrastructure, devices, and managed services sales.

Company Profile:
- Company: {company_name}
- Industry: {industry}
- Size: {employee_count} employees, Revenue: {revenue}
- Tech Stack: {tech_str if tech_str else 'Unknown'}
- Intent Signals: {intent_str if intent_str else 'None detected'}

Pain Points:
{pain_str if pain_str else 'To be determined'}

Available Roles to Choose From:
- CIO (Chief Information Officer) - IT strategy, infrastructure, operations
- CTO (Chief Technology Officer) - Technology innovation, engineering, product tech
- CISO (Chief Information Security Officer) - Cybersecurity, compliance, risk
- CFO (Chief Financial Officer) - Budget, ROI, cost optimization, procurement
- COO (Chief Operating Officer) - Operations efficiency, business continuity
- CPO (Chief Product Officer) - Product development, user experience
- CEO (Chief Executive Officer) - Strategic vision, company direction
- VP of IT - IT operations, infrastructure management
- VP of Operations - Operational efficiency, process improvement
- VP of Engineering - Engineering teams, technical infrastructure

Select the TOP 3 roles most critical for HP's sales success at this company. Consider:
1. Company size and complexity (larger = need IT leadership)
2. Industry requirements (finance/healthcare = need CISO, manufacturing = need COO)
3. Intent signals and pain points (security issues = CISO, cost concerns = CFO)
4. IT infrastructure decision authority

Return ONLY a JSON array of exactly 3 role titles:
["Role1", "Role2", "Role3"]

Examples:
- Enterprise tech company: ["CIO", "CISO", "CFO"]
- Mid-size manufacturer: ["COO", "CIO", "CFO"]
- Financial services: ["CISO", "CIO", "CFO"]
- Healthcare: ["CISO", "CIO", "COO"]"""

            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an HP enterprise sales strategist specializing in identifying key decision-makers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,  # Low temperature for consistent strategic decisions
                max_tokens=100
            )

            import json
            content = response.choices[0].message.content.strip()
            roles = json.loads(content)

            if not isinstance(roles, list) or len(roles) != 3:
                logger.warning(f"LLM returned invalid roles format, using defaults: {roles}")
                # Default based on company size
                if employee_count and isinstance(employee_count, int):
                    if employee_count > 10000:
                        roles = ["CIO", "CISO", "CFO"]
                    elif employee_count > 1000:
                        roles = ["CIO", "CFO", "COO"]
                    else:
                        roles = ["CIO", "CFO", "VP of IT"]
                else:
                    roles = ["CIO", "CFO", "CISO"]  # Universal default

            logger.info(f"Determined strategic roles for {company_name}: {roles}")
            return roles[:3]

        except Exception as e:
            logger.error(f"Failed to determine strategic roles: {e}")
            # Fallback to universal default
            return ["CIO", "CFO", "CISO"]

    async def generate_synthetic_profile(
        self,
        role_title: str,
        company_data: Dict[str, Any],
        pain_points: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete synthetic stakeholder profile for a role when no real contact exists.

        Creates a strategic profile with priorities, communication preferences, and
        conversation starters tailored to the role and company context.

        Args:
            role_title: Role to generate (e.g., "CIO", "CFO", "CISO")
            company_data: Company information for context
            pain_points: Company pain points for relevance

        Returns:
            Complete stakeholder profile dictionary
        """
        try:
            company_name = company_data.get('company_name', 'Company')
            industry = company_data.get('industry', 'Technology')
            employee_count = company_data.get('employee_count', 'Unknown')

            # Format pain points
            pain_str = ""
            if pain_points:
                pain_list = []
                for pain in pain_points[:3]:
                    if isinstance(pain, dict):
                        pain_list.append(pain.get('title', pain.get('name', str(pain))))
                    else:
                        pain_list.append(str(pain))
                pain_str = '\n'.join([f"- {p}" for p in pain_list])

            prompt = f"""Generate a complete strategic profile for the {role_title} at {company_name} ({industry} industry, {employee_count} employees).

Company Pain Points:
{pain_str if pain_str else 'General IT infrastructure and operational efficiency'}

Generate a comprehensive profile with:
1. bio: 2-3 sentence bio describing their role focus and background (realistic, not generic)
2. strategic_priorities: 3 priorities (each with name and description) specific to this role and company
3. communication_preference: Preferred contact methods (e.g., "Email / LinkedIn / Executive Events")
4. conversation_starters: 3 conversation starters (each with topic and specific question) tied to pain points

Format as JSON:
{{
  "bio": "...",
  "strategic_priorities": [
    {{"name": "...", "description": "..."}}
  ],
  "communication_preference": "...",
  "conversation_starters": [
    {{"topic": "...", "question": "..."}}
  ]
}}"""

            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an HP enterprise sales intelligence analyst creating strategic buyer profiles."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=800
            )

            import json
            content = response.choices[0].message.content.strip()
            profile_data = json.loads(content)

            # Build complete synthetic profile
            profile = {
                "name": f"{role_title} (Strategic Contact)",
                "title": role_title,
                "email": "Contact via company website or LinkedIn",
                "phone": "Available upon introduction",
                "linkedin": f"Search LinkedIn: {role_title} at {company_name}",
                "source": "llm_generated",
                "is_synthetic": True,
                **profile_data  # Add bio, strategic_priorities, communication_preference, conversation_starters
            }

            logger.info(f"Generated synthetic profile for {role_title} at {company_name}")
            return profile

        except Exception as e:
            logger.error(f"Failed to generate synthetic profile for {role_title}: {e}")
            # Fallback minimal profile
            return {
                "name": f"{role_title} (Strategic Contact)",
                "title": role_title,
                "email": "Contact via company website",
                "phone": "Available upon introduction",
                "linkedin": "Search on LinkedIn",
                "source": "llm_generated",
                "is_synthetic": True,
                "bio": f"Strategic decision-maker responsible for {role_title} functions at {company_data.get('company_name', 'Company')}.",
                "strategic_priorities": [
                    {"name": "Strategic Initiative", "description": "Leading strategic initiatives for organizational success."}
                ],
                "communication_preference": "Email / LinkedIn",
                "conversation_starters": [
                    {"topic": "Strategic Planning", "question": "What are your top priorities for the coming year?"}
                ]
            }

    async def enrich_stakeholder_profiles(
        self,
        stakeholders: List[Dict[str, str]],
        company_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Enrich stakeholder profiles with strategic priorities and conversation starters.

        Args:
            stakeholders: List of stakeholder basic info
            company_data: Company context

        Returns:
            Enriched stakeholder profiles
        """
        enriched = []

        for stakeholder in stakeholders[:5]:  # Limit to 5 stakeholders
            try:
                title = stakeholder.get('title', '')
                name = stakeholder.get('name', '')

                prompt = f"""For {name}, {title} at {company_data.get('company_name')} ({company_data.get('industry')} industry):

Generate:
1. Three strategic priorities (title + description)
2. Three conversation starters (topic + question)

Format as JSON:
{{
  "strategic_priorities": [
    {{"name": "...", "description": "..."}}
  ],
  "conversation_starters": [
    {{"topic": "...", "question": "..."}}
  ]
}}"""

                response = await openai.ChatCompletion.acreate(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an executive profiler for B2B sales."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    max_tokens=700
                )

                import json
                enrichment = json.loads(response.choices[0].message.content)

                enriched_profile = {
                    **stakeholder,
                    "strategic_priorities": enrichment.get("strategic_priorities", []),
                    "conversation_starters": enrichment.get("conversation_starters", [])
                }

                enriched.append(enriched_profile)

            except Exception as e:
                logger.warning(f"Failed to enrich stakeholder {name}: {e}")
                # Add without enrichment
                enriched.append(stakeholder)

        logger.info(f"Enriched {len(enriched)} stakeholder profiles")
        return enriched
