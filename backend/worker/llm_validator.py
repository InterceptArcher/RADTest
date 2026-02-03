"""
LLM-based data validation module.
Implements validation logic using LLM agents for data quality assurance.

Pre-validation is performed using the DataValidator to catch egregiously
wrong data (like incorrect CEO names) BEFORE sending to the LLM council.
"""
import logging
from typing import Dict, Any, List, Optional
from enum import Enum
import openai
from dataclasses import dataclass

from .data_validator import get_validator, DataValidator

logger = logging.getLogger(__name__)


class ValidationCase(Enum):
    """Types of validation cases."""
    ALL_SAME = "all_same"
    CONFLICTING = "conflicting"
    NULL_DATA = "null_data"


@dataclass
class ValidationResult:
    """Result of data validation."""
    case: ValidationCase
    winner_value: Optional[Any]
    confidence_score: float
    alternatives: List[Any]
    reasoning: str
    rules_applied: List[str]


class LLMValidator:
    """
    Validates data using LLM agents.

    Handles three validation cases:
    1. All data same: Simple consensus validation
    2. Conflicting data: LLM council resolution
    3. NULL data: Fallback strategies

    Pre-validation using DataValidator catches egregiously wrong data
    (like incorrect CEO names for major companies) before LLM processing.
    """

    def __init__(self, openai_api_key: str):
        """
        Initialize LLM validator.

        Args:
            openai_api_key: OpenAI API key (from environment)

        Note:
            This value must be provided via environment variables.
        """
        openai.api_key = openai_api_key
        self.model = "gpt-4"
        self.data_validator = get_validator()
        logger.info("LLM validator initialized with pre-validation enabled")

    def pre_validate_source_data(
        self,
        domain: str,
        source_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Pre-validate data from all sources before LLM processing.

        This catches egregiously wrong data (like incorrect CEO names)
        before it goes to the LLM council, preventing garbage-in-garbage-out.

        Args:
            domain: Company domain (e.g., "microsoft.com")
            source_data: Dict mapping source name to data from that source

        Returns:
            Cleaned source data with corrections applied
        """
        cleaned_data = {}

        for source, data in source_data.items():
            result = self.data_validator.validate_company_data(
                domain=domain,
                data=data,
                source=source
            )

            # Apply corrections
            corrected_data = data.copy()
            for field, corrected_value in result.corrected_values.items():
                logger.warning(
                    f"Pre-validation corrected {field} for {domain} "
                    f"from source {source}: '{data.get(field)}' -> '{corrected_value}'"
                )
                corrected_data[field] = corrected_value

            # Log critical issues
            for issue in result.issues:
                if issue.severity == "critical":
                    logger.error(
                        f"Critical data issue from {source}: "
                        f"{issue.field_name} - {issue.message}"
                    )

            cleaned_data[source] = corrected_data

        return cleaned_data

    def validate_stakeholder_data(
        self,
        domain: str,
        stakeholders: List[Dict[str, Any]],
        source: str = "unknown"
    ) -> List[Dict[str, Any]]:
        """
        Validate stakeholder data and filter out obviously incorrect entries.

        Args:
            domain: Company domain
            stakeholders: List of stakeholder records
            source: Data source name

        Returns:
            Filtered and validated stakeholder list
        """
        result = self.data_validator.validate_company_data(
            domain=domain,
            data={"stakeholders": stakeholders},
            source=source
        )

        # Filter out stakeholders with critical issues
        critical_names = set()
        for issue in result.issues:
            if issue.severity == "critical" and "stakeholder" in issue.field_name:
                # Extract the name that was flagged
                critical_names.add(issue.provided_value)

        validated_stakeholders = []
        for stakeholder in stakeholders:
            name = stakeholder.get("name", "")
            if name not in critical_names:
                validated_stakeholders.append(stakeholder)
            else:
                logger.warning(
                    f"Filtered out stakeholder '{name}' from {source} "
                    f"due to validation failure"
                )

        return validated_stakeholders

    async def validate_field(
        self,
        field_name: str,
        values: List[Dict[str, Any]],
        field_type: str = "text"
    ) -> ValidationResult:
        """
        Validate a single field using LLM agents.

        Args:
            field_name: Name of the field being validated
            values: List of value dictionaries with metadata
                    [{"value": ..., "source": ..., "timestamp": ...}, ...]
            field_type: Type of field (text, numeric, identity)

        Returns:
            ValidationResult with decision and confidence score
        """
        # Determine validation case
        case = self._determine_case(values)

        logger.info(
            f"Validating field '{field_name}' - Case: {case.value}"
        )

        if case == ValidationCase.ALL_SAME:
            return self._validate_all_same(field_name, values)

        elif case == ValidationCase.CONFLICTING:
            return await self._validate_conflicting(
                field_name, values, field_type
            )

        elif case == ValidationCase.NULL_DATA:
            return self._validate_null_data(field_name, values)

    def _determine_case(
        self,
        values: List[Dict[str, Any]]
    ) -> ValidationCase:
        """
        Determine which validation case applies.

        Args:
            values: List of value dictionaries

        Returns:
            ValidationCase enum
        """
        # Check for null/missing data
        non_null_values = [v for v in values if v.get("value") is not None]

        if len(non_null_values) == 0:
            return ValidationCase.NULL_DATA

        # Check if all values are the same
        unique_values = set(str(v.get("value")) for v in non_null_values)

        if len(unique_values) == 1:
            return ValidationCase.ALL_SAME

        return ValidationCase.CONFLICTING

    def _validate_all_same(
        self,
        field_name: str,
        values: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate when all values are the same.

        Args:
            field_name: Name of the field
            values: List of value dictionaries

        Returns:
            ValidationResult with high confidence
        """
        non_null_values = [v for v in values if v.get("value") is not None]
        winner = non_null_values[0]["value"] if non_null_values else None

        logger.info(
            f"Field '{field_name}': All values identical - {winner}"
        )

        return ValidationResult(
            case=ValidationCase.ALL_SAME,
            winner_value=winner,
            confidence_score=1.0,
            alternatives=[],
            reasoning="All data sources provided identical values",
            rules_applied=["consensus"]
        )

    async def _validate_conflicting(
        self,
        field_name: str,
        values: List[Dict[str, Any]],
        field_type: str
    ) -> ValidationResult:
        """
        Validate conflicting data using LLM council.

        Args:
            field_name: Name of the field
            values: List of value dictionaries with conflicting data
            field_type: Type of field

        Returns:
            ValidationResult with LLM decision
        """
        logger.info(
            f"Field '{field_name}': Resolving conflict with LLM council"
        )

        # Prepare prompt for LLM
        prompt = self._create_validation_prompt(
            field_name, values, field_type
        )

        try:
            # Call LLM for resolution
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a data validation expert. "
                            "Analyze conflicting data from multiple sources "
                            "and determine the most accurate value."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )

            # Parse LLM response
            result = self._parse_llm_response(
                response.choices[0].message.content,
                values
            )

            logger.info(
                f"Field '{field_name}': LLM selected value with "
                f"confidence {result.confidence_score}"
            )

            return result

        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            # Fallback to simple heuristics
            return self._fallback_resolution(field_name, values, field_type)

    def _validate_null_data(
        self,
        field_name: str,
        values: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Handle NULL/missing data case.

        Args:
            field_name: Name of the field
            values: List of value dictionaries

        Returns:
            ValidationResult indicating missing data
        """
        logger.warning(f"Field '{field_name}': All data is NULL")

        return ValidationResult(
            case=ValidationCase.NULL_DATA,
            winner_value=None,
            confidence_score=0.0,
            alternatives=[],
            reasoning="No data available from any source",
            rules_applied=["null_handling"]
        )

    def _create_validation_prompt(
        self,
        field_name: str,
        values: List[Dict[str, Any]],
        field_type: str
    ) -> str:
        """
        Create prompt for LLM validation.

        Args:
            field_name: Name of the field
            values: List of value dictionaries
            field_type: Type of field

        Returns:
            Formatted prompt string
        """
        prompt = f"Field: {field_name} (Type: {field_type})\n\n"
        prompt += "Conflicting values from different sources:\n\n"

        for i, val_dict in enumerate(values, 1):
            prompt += f"{i}. Value: {val_dict['value']}\n"
            prompt += f"   Source: {val_dict.get('source', 'unknown')}\n"
            prompt += f"   Timestamp: {val_dict.get('timestamp', 'unknown')}\n"
            prompt += f"   Reliability: {val_dict.get('reliability', 'medium')}\n\n"

        prompt += (
            "Please analyze these values and determine:\n"
            "1. Which value is most likely correct\n"
            "2. Confidence score (0-1)\n"
            "3. Brief reasoning\n"
            "4. Alternative values ranked by likelihood\n\n"
            "Consider: source reliability, recency, cross-source agreement, "
            "and data type-specific validation rules.\n\n"
            "Response format:\n"
            "WINNER: <value>\n"
            "CONFIDENCE: <0-1>\n"
            "REASONING: <explanation>\n"
            "ALTERNATIVES: <comma-separated values>"
        )

        return prompt

    def _parse_llm_response(
        self,
        response_text: str,
        original_values: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Parse LLM response into ValidationResult.

        Args:
            response_text: Raw LLM response
            original_values: Original value dictionaries

        Returns:
            ValidationResult
        """
        lines = response_text.strip().split("\n")
        winner = None
        confidence = 0.5
        reasoning = ""
        alternatives = []

        for line in lines:
            if line.startswith("WINNER:"):
                winner = line.replace("WINNER:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(
                        line.replace("CONFIDENCE:", "").strip()
                    )
                except ValueError:
                    confidence = 0.5
            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()
            elif line.startswith("ALTERNATIVES:"):
                alt_text = line.replace("ALTERNATIVES:", "").strip()
                alternatives = [a.strip() for a in alt_text.split(",")]

        return ValidationResult(
            case=ValidationCase.CONFLICTING,
            winner_value=winner,
            confidence_score=confidence,
            alternatives=alternatives,
            reasoning=reasoning,
            rules_applied=["llm_council", "source_reliability"]
        )

    def _fallback_resolution(
        self,
        field_name: str,
        values: List[Dict[str, Any]],
        field_type: str
    ) -> ValidationResult:
        """
        Fallback resolution when LLM is unavailable.

        Uses simple heuristics:
        - Prefer higher reliability sources
        - Prefer more recent data
        - Prefer most common value

        Args:
            field_name: Name of the field
            values: List of value dictionaries
            field_type: Type of field

        Returns:
            ValidationResult
        """
        logger.info(f"Using fallback resolution for '{field_name}'")

        # Sort by reliability and recency
        sorted_values = sorted(
            values,
            key=lambda x: (
                x.get("reliability_score", 0),
                x.get("timestamp", "")
            ),
            reverse=True
        )

        winner = sorted_values[0]["value"]
        alternatives = [v["value"] for v in sorted_values[1:]]

        return ValidationResult(
            case=ValidationCase.CONFLICTING,
            winner_value=winner,
            confidence_score=0.6,
            alternatives=alternatives,
            reasoning="Fallback resolution based on source reliability",
            rules_applied=["fallback", "source_reliability"]
        )
